from rest_framework import serializers

_SUBJECT_AREAS   = ['stem', 'humanities', 'languages', 'arts', 'general']
_TEACHING_LEVELS = ['primary', 'secondary', 'higher_ed', 'vocational', 'adult_ed']
_ANSWER_KEYS     = {'q3', 'q4', 'q5'}
_ANSWER_OPTIONS  = {'a', 'b', 'c', 'd'}
_GOALS           = ['save_time', 'teach_about_ai', 'prepare_students', 'stay_current', 'address_ethics']


class OnboardingSubmitSerializer(serializers.Serializer):
    subject_area   = serializers.ChoiceField(choices=_SUBJECT_AREAS)
    teaching_level = serializers.ChoiceField(choices=_TEACHING_LEVELS)
    answers        = serializers.DictField(child=serializers.ChoiceField(choices=_ANSWER_OPTIONS))
    goals          = serializers.ListField(
        child=serializers.ChoiceField(choices=_GOALS),
        allow_empty=True,
    )

    def validate_answers(self, value):
        for key in value:
            if key not in _ANSWER_KEYS:
                raise serializers.ValidationError(f"Unknown question key: {key}")
        return value
