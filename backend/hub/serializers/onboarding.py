from rest_framework import serializers

from hub.models import OnboardingQuestion, Subject
from hub.self_efficacy import LIKERT_MAX, LIKERT_MIN

_TEACHING_LEVELS = ['primary', 'secondary', 'higher_ed', 'vocational', 'adult_ed']
_GOALS           = ['save_time', 'teach_about_ai', 'prepare_students', 'stay_current', 'address_ethics']


def _localized(obj, field, lang):
    """The translation for the viewer's language, falling back to the base value."""
    if lang:
        value = (obj.translations or {}).get(lang)
        if value:
            return value
    return getattr(obj, field)


class OnboardingQuestionSerializer(serializers.ModelSerializer):
    """A single self-efficacy statement (no answer options — shared Likert)."""
    text = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingQuestion
        fields = ['id', 'text']

    def get_text(self, obj):
        return _localized(obj, 'text', self.context.get('lang'))


class OnboardingDimensionSerializer(serializers.Serializer):
    """A dimension with its active questions, localized to the viewer."""
    id = serializers.IntegerField()
    slug = serializers.CharField()
    name = serializers.SerializerMethodField()
    order = serializers.IntegerField()
    questions = serializers.SerializerMethodField()

    def get_name(self, obj):
        return _localized(obj, 'name', self.context.get('lang'))

    def get_questions(self, obj):
        active = [q for q in obj.questions.all() if q.is_active]
        return OnboardingQuestionSerializer(active, many=True, context=self.context).data


class OnboardingSubmitSerializer(serializers.Serializer):
    """Quick profile step completed at registration (no competency answers)."""
    subject        = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.filter(is_active=True),
    )
    teaching_level = serializers.ChoiceField(choices=_TEACHING_LEVELS)
    goals          = serializers.ListField(
        child=serializers.ChoiceField(choices=_GOALS),
        allow_empty=True,
    )


class SelfEfficacySubmitSerializer(serializers.Serializer):
    """Partial or full save of Likert answers: {question_id: 1-5}."""
    answers = serializers.DictField(child=serializers.IntegerField())

    def validate_answers(self, value):
        active_ids = set(
            OnboardingQuestion.objects.filter(is_active=True).values_list('id', flat=True)
        )
        cleaned = {}
        for qid_str, rating in value.items():
            try:
                qid = int(qid_str)
            except (TypeError, ValueError):
                raise serializers.ValidationError(f'Invalid question id: {qid_str!r}.')
            if qid not in active_ids:
                raise serializers.ValidationError(f'Unknown or inactive question: {qid}.')
            if not (LIKERT_MIN <= rating <= LIKERT_MAX):
                raise serializers.ValidationError(
                    f'Rating for question {qid} must be between {LIKERT_MIN} and {LIKERT_MAX}.'
                )
            cleaned[qid] = rating
        return cleaned
