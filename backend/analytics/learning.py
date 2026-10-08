"""Per-course learning analytics from measured visits and events — see
docs/superpowers/specs/2026-10-01-learning-analytics-design.md.

CourseData loads one course's structure and every enrolled learner's data
once; the web endpoints (content tree, learners, timeline) and the Excel
workbook all read from it, so they always agree. Module and activity times
are sums over resource visits."""
from collections import defaultdict
from datetime import timedelta
from statistics import mean, median

from django.utils import timezone

from hub.completion import activity_completion
from hub.models import (
    Activity,
    AssignmentSubmission,
    Enrollment,
    LearnerActivityConfig,
    LearningEvent,
    Module,
    Resource,
    ResourceProgress,
    ResourceVisit,
)

INACTIVE_DAYS = 14       # no activity for this long → inactive (and "dropped here")
STUCK_VISITS = 3         # this many visits to one resource without finishing it → stuck
VIDEO_FINISHED_PCT = 90  # watching less than this counts as stopping early


def display_name(user):
    return user.get_full_name() or user.username


def resource_label(resource):
    return resource.title or f'{resource.get_type_display()} {resource.order}'


def time_summary(visits):
    """Active / on-screen seconds, page visits and first / last time of visits."""
    visits = list(visits)
    return {
        'active_s': sum(v.active_seconds for v in visits),
        'visible_s': sum(v.visible_seconds for v in visits),
        'visits': len({v.page_key for v in visits}),
        'first_opened': min((v.started_at for v in visits), default=None),
        'last_seen': max((v.last_seen_at for v in visits), default=None),
    }


class CourseData:
    def __init__(self, course, now=None):
        self.course = course
        self.now = now or timezone.now()
        self.modules = list(Module.objects.filter(course=course).order_by('order', 'id'))
        self.activities_of = defaultdict(list)
        for activity in Activity.objects.filter(module__course=course).order_by('order', 'id'):
            self.activities_of[activity.module_id].append(activity)
        self.resources = list(
            Resource.objects.filter(activity__module__course=course)
            .select_related('activity__module')
            .order_by('activity__module__order', 'activity__module_id', 'activity__order',
                      'activity_id', 'order', 'id')
        )
        self.resources_of = defaultdict(list)
        for resource in self.resources:
            self.resources_of[resource.activity_id].append(resource)
        self.resource_by_id = {r.id: r for r in self.resources}

        self.enrollments = list(
            Enrollment.objects.filter(course=course)
            .select_related('user__profile__subject', 'user__study')
            .order_by('user__first_name', 'user__last_name', 'user__username')
        )
        user_ids = [e.user_id for e in self.enrollments]

        self._visits = defaultdict(list)
        for v in ResourceVisit.objects.filter(course=course, user_id__in=user_ids).order_by('started_at'):
            for key in (('u', v.user_id), ('r', v.user_id, v.resource_id),
                        ('a', v.user_id, v.activity_id), ('m', v.user_id, v.module_id)):
                self._visits[key].append(v)
        self._events = defaultdict(list)
        for e in LearningEvent.objects.filter(course=course, user_id__in=user_ids).order_by('occurred_at', 'id'):
            self._events[(e.user_id, e.resource_id)].append(e)
        self._progress = {}
        self._progress_of = defaultdict(list)
        for p in ResourceProgress.objects.filter(resource__activity__module__course=course, user_id__in=user_ids):
            self._progress[(p.user_id, p.resource_id)] = p
            self._progress_of[p.user_id].append(p)
        self.submissions = {}
        for s in (AssignmentSubmission.objects
                  .filter(resource__activity__module__course=course, user_id__in=user_ids)
                  .order_by('submitted_at')):
            self.submissions[(s.user_id, s.resource_id)] = s  # latest wins
        self._submissions_of = defaultdict(list)
        for s in self.submissions.values():
            self._submissions_of[s.user_id].append(s)
        self._completion = {e.user_id: activity_completion(e.user, course) for e in self.enrollments}
        self.pass_threshold = LearnerActivityConfig.get().quiz_pass_threshold

    # ── Raw lookups ──────────────────────────────────────────────────────────

    def user_visits(self, uid):
        return self._visits.get(('u', uid), [])

    def resource_visits(self, uid, rid):
        return self._visits.get(('r', uid, rid), [])

    def activity_visits(self, uid, aid):
        return self._visits.get(('a', uid, aid), [])

    def module_visits(self, uid, mid):
        return self._visits.get(('m', uid, mid), [])

    def events_for(self, uid, rid, *types):
        events = self._events.get((uid, rid), [])
        return [e for e in events if e.event_type in types] if types else events

    def progress_for(self, uid, rid):
        return self._progress.get((uid, rid))

    def completed_at(self, uid, rid):
        progress = self.progress_for(uid, rid)
        return progress.completed_at if progress else None

    def reached(self, uid, rid):
        """Opened at least once: a measured visit, or progress from before tracking."""
        return bool(self.resource_visits(uid, rid)) or (uid, rid) in self._progress

    # ── Completion ───────────────────────────────────────────────────────────

    def activity_done(self, uid, aid):
        return aid in self._completion[uid][2]

    def module_pct(self, uid, mid):
        """% of the module's required activities done (all activities when none
        is required); None for a module without activities."""
        required, completed_required, completed = self._completion[uid]
        ids = [a.id for a in self.activities_of.get(mid, [])]
        req = [i for i in ids if i in required]
        if req:
            return round(100 * sum(i in completed_required for i in req) / len(req))
        if ids:
            return round(100 * sum(i in completed for i in ids) / len(ids))
        return None

    # ── Per-resource detail ──────────────────────────────────────────────────

    def video_pct(self, uid, rid):
        """% of the video played in the learner's best single visit."""
        values = [v.media_progress.get('covered_pct') for v in self.resource_visits(uid, rid)]
        values = [x for x in values if isinstance(x, (int, float))]
        return max(values) if values else None

    def video_furthest(self, uid, rid):
        values = [v.media_progress.get('furthest_s') for v in self.resource_visits(uid, rid)]
        values = [x for x in values if isinstance(x, (int, float))]
        return max(values) if values else None

    def quiz_answers(self, uid, resource):
        """One dict per answered question of a quiz. Stored results win over
        recomputation, so a quiz edited later still reports what was scored."""
        progress = self.progress_for(uid, resource.id)
        done = progress is not None and progress.completed_at is not None
        selected = (progress.engagement_data or {}).get('quiz_selected', []) if progress else []
        stored = (progress.quiz_answers or []) if progress else []
        timing = {}
        for e in self.events_for(uid, resource.id, LearningEvent.Type.QUIZ_ANSWER):
            if isinstance(e.data.get('question_index'), int):
                timing[e.data['question_index']] = e  # the last answer wins
        rows = []
        for i, question in enumerate(resource.quiz_data or []):
            event = timing.get(i)
            if not done and event is None:
                continue
            options = question.get('options', [])
            pick = selected[i] if i < len(selected) else (event.data.get('selected') if event else None)
            valid = isinstance(pick, int) and 0 <= pick < len(options)
            if i < len(stored):
                right = bool(stored[i])
            elif valid:
                right = bool(options[pick].get('is_correct'))
            else:
                right = None
            rows.append({
                'index': i,
                'question': question.get('question', ''),
                'selected_text': options[pick].get('text') if valid else None,
                'correct_text': next((o.get('text') for o in options if o.get('is_correct')), None),
                'is_correct': right,
                'seconds': event.data.get('seconds_on_question') if event else None,
                'answered_at': event.occurred_at if event else (progress.completed_at if done else None),
            })
        return rows

    def _h5p_attempt_numbers(self, uid, resource):
        """Number H5P attempts in time order. An attempt ends when it finishes,
        or — unfinished — when the learner answers again in a new page visit.
        Returns ([(number, attempt event)], [(number, answer event)])."""
        kinds = (LearningEvent.Type.H5P_ATTEMPT, LearningEvent.Type.H5P_ANSWER)
        events = sorted(self.events_for(uid, resource.id, *kinds), key=lambda e: (e.occurred_at, e.id))
        finished, answers = [], []
        number, open_visit, open_has_answers = 1, None, False
        for e in events:
            if e.event_type == LearningEvent.Type.H5P_ANSWER:
                if open_has_answers and e.visit_id != open_visit:
                    number += 1  # the previous visit's attempt was abandoned
                answers.append((number, e))
                open_visit, open_has_answers = e.visit_id, True
            else:
                finished.append((number, e))
                number += 1
                open_visit, open_has_answers = None, False
        return finished, answers

    def h5p_attempts(self, uid, resource):
        """Finished H5P attempts in time order, with their attempt numbers
        (an abandoned attempt uses a number too)."""
        finished, _ = self._h5p_attempt_numbers(uid, resource)
        return [{
            'number': n, 'raw': e.data.get('raw'), 'max': e.data.get('max'),
            'success': e.data.get('success'), 'duration_s': e.data.get('duration_s'),
            'language': e.data.get('language', ''), 'finished_at': e.occurred_at,
        } for n, e in finished]

    def h5p_answers(self, uid, resource):
        """H5P answers with the number of the attempt they belong to."""
        _, answers = self._h5p_attempt_numbers(uid, resource)
        return [{
            'attempt': n, 'question': e.data.get('question', ''),
            'response': e.data.get('response', ''), 'correct': e.data.get('correct'),
            'raw': e.data.get('raw'), 'max': e.data.get('max'),
            'seconds': e.data.get('seconds'), 'answered_at': e.occurred_at,
        } for n, e in answers]

    def resource_detail(self, uid, resource):
        progress = self.progress_for(uid, resource.id)
        engagement = (progress.engagement_data or {}) if progress else {}
        submission = self.submissions.get((uid, resource.id))
        kind = resource.type

        def count(*types):
            return len(self.events_for(uid, resource.id, *types))

        return {
            **time_summary(self.resource_visits(uid, resource.id)),
            'completed_at': progress.completed_at if progress else None,
            'quiz_score': progress.quiz_score if progress and kind in ('quiz', 'h5p') else None,
            'h5p_attempts': count('h5p_attempt') if kind == 'h5p' else None,
            'video_pct': self.video_pct(uid, resource.id) if kind == 'video' else None,
            'scroll_pct': engagement.get('scroll_pct') if kind == 'text' else None,
            'pdf_opened': count('pdf_open') if kind == 'pdf' else None,
            'pdf_downloaded': count('pdf_download') if kind == 'pdf' else None,
            'image_opened': count('image_open') if kind == 'image' else None,
            'assignment_status': submission.status if submission else None,
        }

    # ── Learner state ────────────────────────────────────────────────────────

    def last_active(self, enrollment):
        uid = enrollment.user_id
        times = [enrollment.enrolled_at]
        times += [v.last_seen_at for v in self.user_visits(uid)]
        times += [p.updated_at for p in self._progress_of.get(uid, [])]
        times += [s.submitted_at for s in self._submissions_of.get(uid, [])]
        return max(times)

    def position(self, uid):
        """The resource the learner touched last (visit or progress)."""
        moments = [(v.last_seen_at, v.resource_id) for v in self.user_visits(uid)]
        moments += [(p.updated_at, p.resource_id) for p in self._progress_of.get(uid, [])]
        if not moments:
            return None
        return self.resource_by_id.get(max(moments, key=lambda m: m[0])[1])

    def _stuck(self, uid):
        for resource in self.resources:
            if (self.completed_at(uid, resource.id) is None
                    and len(self.resource_visits(uid, resource.id)) >= STUCK_VISITS):
                return True
            progress = self.progress_for(uid, resource.id)
            if (resource.type in ('quiz', 'h5p') and progress and progress.quiz_score is not None
                    and progress.quiz_score < self.pass_threshold):
                return True
        return False

    def status(self, enrollment):
        if enrollment.completed_at is not None or enrollment.progress_pct >= 100:
            return 'completed'
        if self.now - self.last_active(enrollment) >= timedelta(days=INACTIVE_DAYS):
            return 'inactive'
        if self._stuck(enrollment.user_id):
            return 'stuck'
        return 'on_track'

    def dropped_at(self, enrollment):
        """Where an unfinished learner with no activity for 14+ days stopped."""
        return self.position(enrollment.user_id) if self.status(enrollment) == 'inactive' else None


# ── Content tree ─────────────────────────────────────────────────────────────


def _level_stats(rows):
    """rows: one (reached, done, active_s or None when unmeasured, dropped) per learner."""
    times = [active for reached, _, active, _ in rows if reached and active is not None]
    return {
        'reached': sum(1 for reached, *_ in rows if reached),
        'done': sum(1 for _, done, *_ in rows if done),
        'median_active_s': round(median(times)) if times else None,
        'mean_active_s': round(mean(times)) if times else None,
        'dropped': sum(1 for *_, dropped in rows if dropped),
    }


def _measured(visits):
    return sum(v.active_seconds for v in visits) if visits else None


def _avg(values, digits=0):
    if not values:
        return None
    value = round(mean(values), digits)
    return int(value) if digits == 0 else value


def resource_notes(cd, resource):
    uids = [e.user_id for e in cd.enrollments]
    kind = resource.type
    if kind == 'text':
        scrolls = []
        for uid in uids:
            progress = cd.progress_for(uid, resource.id)
            value = (progress.engagement_data or {}).get('scroll_pct') if progress else None
            if isinstance(value, (int, float)):
                scrolls.append(value)
        return {'avg_scroll_pct': _avg(scrolls)}
    if kind == 'video':
        watched, stops = [], []
        for uid in uids:
            pct = cd.video_pct(uid, resource.id)
            if pct is None:
                continue
            watched.append(pct)
            furthest = cd.video_furthest(uid, resource.id)
            if pct < VIDEO_FINISHED_PCT and furthest is not None:
                stops.append(furthest)
        return {'avg_watched_pct': _avg(watched), 'typical_stop_s': round(median(stops)) if stops else None}
    if kind == 'quiz':
        scores = [p.quiz_score for uid in uids
                  if (p := cd.progress_for(uid, resource.id)) and p.quiz_score is not None]
        right_by_question, seconds = defaultdict(list), []
        for uid in uids:
            for answer in cd.quiz_answers(uid, resource):
                if answer['is_correct'] is not None:
                    right_by_question[answer['index']].append(answer['is_correct'])
                if isinstance(answer['seconds'], (int, float)):
                    seconds.append(answer['seconds'])
        hardest = min(right_by_question.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), default=None)
        return {
            'avg_score_pct': _avg([s * 100 for s in scores]),
            'hardest_question': {
                'number': hardest[0] + 1,
                'question': resource.quiz_data[hardest[0]].get('question', ''),
                'pct_correct': round(100 * sum(hardest[1]) / len(hardest[1])),
            } if hardest else None,
            'avg_seconds_per_question': _avg(seconds, 1),
        }
    if kind == 'h5p':
        scores, attempts, right_by_question = [], [], defaultdict(list)
        finished = 0
        for uid in uids:
            progress = cd.progress_for(uid, resource.id)
            if progress and progress.completed_at:
                finished += 1
            if progress and progress.quiz_score is not None:
                scores.append(progress.quiz_score)
            count = len(cd.h5p_attempts(uid, resource))
            if count:
                attempts.append(count)
            for answer in cd.h5p_answers(uid, resource):
                if isinstance(answer['correct'], bool) and answer['question']:
                    right_by_question[answer['question']].append(answer['correct'])
        hardest = min(right_by_question.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), default=None)
        return {
            'finished': finished,
            'avg_score_pct': _avg([s * 100 for s in scores]),
            'avg_attempts': _avg(attempts, 1),
            'hardest_question': {
                'question': hardest[0], 'pct_correct': round(100 * sum(hardest[1]) / len(hardest[1])),
            } if hardest else None,
        }
    if kind in ('pdf', 'image'):
        opened = sum(1 for uid in uids if cd.events_for(uid, resource.id, f'{kind}_open'))
        if kind == 'image':
            return {'opened': opened}
        downloaded = sum(1 for uid in uids if cd.events_for(uid, resource.id, 'pdf_download'))
        return {'opened': opened, 'downloaded': downloaded}
    if kind == 'assignment':
        statuses = [s.status for uid in uids if (s := cd.submissions.get((uid, resource.id)))]
        status = AssignmentSubmission.Status
        return {
            'submitted': len(statuses),
            'approved': statuses.count(status.APPROVED),
            'waiting': statuses.count(status.PENDING),
            'changes_requested': statuses.count(status.CHANGES_REQUESTED),
        }
    return {}


def content_tree(cd):
    uids = [e.user_id for e in cd.enrollments]
    drops = {e.user_id: cd.dropped_at(e) for e in cd.enrollments}
    reached = {uid: {r.id for r in cd.resources if cd.reached(uid, r.id)} for uid in uids}

    def dropped(uid, test):
        return drops[uid] is not None and test(drops[uid])

    modules = []
    for module in cd.modules:
        activities = []
        for activity in cd.activities_of.get(module.id, []):
            resources = []
            for r in cd.resources_of.get(activity.id, []):
                rows = [(r.id in reached[uid], cd.completed_at(uid, r.id) is not None,
                         _measured(cd.resource_visits(uid, r.id)),
                         dropped(uid, lambda d, r=r: d.id == r.id)) for uid in uids]
                resources.append({
                    'id': r.id, 'title': resource_label(r), 'type': r.type, 'order': r.order,
                    'is_required': r.is_required, 'stats': _level_stats(rows),
                    'notes': resource_notes(cd, r),
                })
            ids = {r.id for r in cd.resources_of.get(activity.id, [])}
            rows = [(bool(ids & reached[uid]), cd.activity_done(uid, activity.id),
                     _measured(cd.activity_visits(uid, activity.id)),
                     dropped(uid, lambda d, a=activity: d.activity_id == a.id)) for uid in uids]
            activities.append({
                'id': activity.id, 'title': activity.title, 'order': activity.order,
                'stats': _level_stats(rows), 'resources': resources,
            })
        ids = {r.id for a in cd.activities_of.get(module.id, []) for r in cd.resources_of.get(a.id, [])}
        rows = [(bool(ids & reached[uid]), cd.module_pct(uid, module.id) == 100,
                 _measured(cd.module_visits(uid, module.id)),
                 dropped(uid, lambda d, m=module: d.activity.module_id == m.id)) for uid in uids]
        modules.append({
            'id': module.id, 'title': module.title, 'order': module.order,
            'stats': _level_stats(rows), 'activities': activities,
        })
    return {
        'course': {'id': cd.course.id, 'title': cd.course.title},
        'learners': len(uids),
        'modules': modules,
    }


# ── Learners ─────────────────────────────────────────────────────────────────


def _position_dict(resource):
    if resource is None:
        return None
    return {
        'resource_id': resource.id,
        'resource': resource_label(resource),
        'activity': resource.activity.title,
        'module': resource.activity.module.title,
    }


def learner_row(cd, enrollment):
    user = enrollment.user
    totals = time_summary(cd.user_visits(user.id))
    return {
        'user_id': user.id,
        'name': display_name(user),
        'email': user.email,
        'enrolled_at': enrollment.enrolled_at,
        'completed_at': enrollment.completed_at,
        'progress_pct': enrollment.progress_pct,
        'active_s': totals['active_s'],
        'visible_s': totals['visible_s'],
        'visits': totals['visits'],
        'tracked': bool(cd.user_visits(user.id)),
        'last_active': cd.last_active(enrollment),
        'position': _position_dict(cd.position(user.id)),
        'status': cd.status(enrollment),
    }


def learner_rows(cd):
    return [learner_row(cd, e) for e in cd.enrollments]


def learner_timeline(cd, user_id):
    """One learner's module → activity → resource tree, or None if not enrolled."""
    enrollment = next((e for e in cd.enrollments if e.user_id == user_id), None)
    if enrollment is None:
        return None
    modules = []
    for module in cd.modules:
        activities = []
        for activity in cd.activities_of.get(module.id, []):
            resources = [{
                'id': r.id, 'title': resource_label(r), 'type': r.type, 'order': r.order,
                'is_required': r.is_required,
                **cd.resource_detail(user_id, r),
                'quiz_answers': cd.quiz_answers(user_id, r) if r.type == 'quiz' else None,
                'h5p': {
                    'attempts': cd.h5p_attempts(user_id, r), 'answers': cd.h5p_answers(user_id, r),
                } if r.type == 'h5p' else None,
            } for r in cd.resources_of.get(activity.id, [])]
            activities.append({
                'id': activity.id, 'title': activity.title, 'order': activity.order,
                'done': cd.activity_done(user_id, activity.id),
                **time_summary(cd.activity_visits(user_id, activity.id)),
                'resources': resources,
            })
        modules.append({
            'id': module.id, 'title': module.title, 'order': module.order,
            'pct': cd.module_pct(user_id, module.id),
            **time_summary(cd.module_visits(user_id, module.id)),
            'activities': activities,
        })
    return {'learner': learner_row(cd, enrollment), 'modules': modules}
