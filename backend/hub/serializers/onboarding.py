from rest_framework import serializers

from hub.models import OnboardingOption, OnboardingQuestion, Subject

_TEACHING_LEVELS = ['primary', 'secondary', 'higher_ed', 'vocational', 'adult_ed']
_GOALS           = ['save_time', 'teach_about_ai', 'prepare_students', 'stay_current', 'address_ethics']


class OnboardingOptionSerializer(serializers.ModelSerializer):
    """Learner-facing option — never exposes the score."""
    class Meta:
        model = OnboardingOption
        fields = ['id', 'text']


class OnboardingQuestionSerializer(serializers.ModelSerializer):
    options = OnboardingOptionSerializer(many=True, read_only=True)

    class Meta:
        model = OnboardingQuestion
        fields = ['id', 'text', 'options']


class OnboardingSubmitSerializer(serializers.Serializer):
    subject        = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.filter(is_active=True),
    )
    teaching_level = serializers.ChoiceField(choices=_TEACHING_LEVELS)
    # {question_id: option_id} — one chosen option per active question.
    answers        = serializers.DictField(child=serializers.IntegerField())
    goals          = serializers.ListField(
        child=serializers.ChoiceField(choices=_GOALS),
        allow_empty=True,
    )

    def validate_answers(self, value):
        questions = {
            q.id: q
            for q in OnboardingQuestion.objects.filter(is_active=True).prefetch_related('options')
        }
        chosen = {}
        for qid_str, oid in value.items():
            try:
                qid = int(qid_str)
            except (TypeError, ValueError):
                raise serializers.ValidationError(f'Invalid question id: {qid_str!r}.')
            question = questions.get(qid)
            if question is None:
                raise serializers.ValidationError(f'Unknown or inactive question: {qid}.')
            option = next((o for o in question.options.all() if o.id == oid), None)
            if option is None:
                raise serializers.ValidationError(f'Option {oid} does not belong to question {qid}.')
            chosen[qid] = option

        missing = set(questions) - set(chosen)
        if missing:
            raise serializers.ValidationError('All questions must be answered.')
        return chosen
