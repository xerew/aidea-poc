"""Authoring endpoints for an assignment's AI review set-up."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.ai_review import model
from hub.ai_review.pipeline import assignment_stats, auto_approve_unlocked
from hub.models import AIReviewSettings, AssignmentReviewConfig, Resource, ReviewExample

from .permissions import IsContentCreator, can_edit_course

MAX_CRITERIA = 10
MAX_EXAMPLES = 5
FLAGS = ('enabled', 'learner_visible', 'duplicate_check')


def _resource(request, pk, module_pk, lesson_pk, resource_pk):
    resource = (Resource.objects.select_related('activity__module__course')
                .filter(pk=resource_pk, activity_id=lesson_pk, activity__module_id=module_pk,
                        activity__module__course_id=pk).first())
    if resource is None:
        return None, Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not can_edit_course(request.user, resource.activity.module.course):
        return None, Response({'detail': 'You cannot edit this course.'}, status=status.HTTP_403_FORBIDDEN)
    if resource.type != Resource.Type.ASSIGNMENT:
        return None, Response({'detail': 'AI review is only for assignments.'}, status=status.HTTP_400_BAD_REQUEST)
    return resource, None


def _clean_criteria(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_CRITERIA:
        return None
    cleaned = []
    for i, c in enumerate(raw, start=1):
        if not isinstance(c, dict) or not str(c.get('name', '')).strip() or not isinstance(c.get('required', True), bool):
            return None
        cleaned.append({'id': str(c.get('id') or f'c{i}')[:20], 'name': str(c['name']).strip()[:120],
                        'met': str(c.get('met', '')).strip()[:500], 'required': c.get('required', True)})
    if len({c['id'] for c in cleaned}) != len(cleaned):
        return None
    return cleaned


def _payload(config):
    settings = AIReviewSettings.get()
    return {
        'enabled': config.enabled, 'criteria': config.criteria, 'rubric_approved': config.rubric_approved,
        'learner_visible': config.learner_visible, 'auto_approve': config.auto_approve,
        'duplicate_check': config.duplicate_check, 'platform_enabled': settings.enabled,
        'unlocked': auto_approve_unlocked(config.resource, settings),
        'unlock_min_reviews': settings.unlock_min_reviews,
        'unlock_min_lower_bound': settings.unlock_min_lower_bound,
        'stats': assignment_stats(config.resource),
    }


class AuthoringAIReviewView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        config, _ = AssignmentReviewConfig.objects.get_or_create(resource=resource)
        return Response(_payload(config))

    def put(self, request, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        config, _ = AssignmentReviewConfig.objects.get_or_create(resource=resource)
        data = request.data
        if 'criteria' in data:
            criteria = _clean_criteria(data['criteria'])
            if criteria is None:
                return Response({'detail': 'Invalid criteria.'}, status=status.HTTP_400_BAD_REQUEST)
            if criteria != config.criteria:
                config.criteria, config.rubric_approved = criteria, False
        for flag in FLAGS:
            if flag in data:
                setattr(config, flag, bool(data[flag]))
        newly_approved = False
        if data.get('rubric_approved') is True and config.criteria:
            newly_approved = not config.rubric_approved
            config.rubric_approved = True
        if 'auto_approve' in data:
            wanted = bool(data['auto_approve'])
            if wanted and not auto_approve_unlocked(resource, AIReviewSettings.get()):
                return Response({'detail': 'Auto-approve unlocks after enough agreeing reviews.'},
                                status=status.HTTP_400_BAD_REQUEST)
            config.auto_approve = wanted
        config.save()
        if newly_approved:
            from hub.tasks import translate_review_criteria
            translate_review_criteria.delay(config.id)
            config.refresh_from_db()
        return Response(_payload(config))


class AuthoringAIReviewDraftView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        course = resource.activity.module.course
        try:
            criteria = model.draft_rubric(
                title=resource.title or resource.activity.title, instructions=resource.instructions,
                language=course.source_language or 'en', model=AIReviewSettings.get().model_name,
            )
        except model.ModelOffline:
            return Response({'detail': 'The AI server is not reachable right now.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except model.ReviewModelError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'criteria': criteria})


class AuthoringAIReviewExamplesView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        return Response([_example(e) for e in resource.ai_review_examples.all()])

    def post(self, request, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        if resource.ai_review_examples.count() >= MAX_EXAMPLES:
            return Response({'detail': f'At most {MAX_EXAMPLES} examples.'}, status=status.HTTP_400_BAD_REQUEST)
        verdict = request.data.get('verdict')
        text = str(request.data.get('text', '')).strip()
        if verdict not in ('approve', 'changes_requested') or not text:
            return Response({'detail': 'An example needs text and a verdict.'}, status=status.HTTP_400_BAD_REQUEST)
        example = ReviewExample.objects.create(resource=resource, text=text[:8000], verdict=verdict,
                                               reason=str(request.data.get('reason', ''))[:1000], created_by=request.user)
        return Response(_example(example), status=status.HTTP_201_CREATED)


class AuthoringAIReviewExampleView(APIView):
    permission_classes = [IsContentCreator]

    def delete(self, request, example_pk, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        deleted, _ = resource.ai_review_examples.filter(pk=example_pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT if deleted else status.HTTP_404_NOT_FOUND)


def _example(e):
    return {'id': e.id, 'text': e.text, 'verdict': e.verdict, 'reason': e.reason,
            'from_submission': e.source_submission_id is not None, 'created_at': e.created_at}
