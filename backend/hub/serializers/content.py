from rest_framework import serializers

from hub.models import Lesson, Module


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'description', 'lesson_type',
            'content', 'quiz_data', 'duration_minutes', 'order', 'is_required',
        ]

    def validate_quiz_data(self, value):
        """Ensure quiz_data is a valid list of questions with options."""
        if not isinstance(value, list):
            raise serializers.ValidationError('quiz_data must be a list.')
        for i, question in enumerate(value):
            if not isinstance(question, dict):
                raise serializers.ValidationError(f'Question {i + 1} must be an object.')
            if not isinstance(question.get('question', ''), str):
                raise serializers.ValidationError(f'Question {i + 1} must have a string "question" field.')
            options = question.get('options', [])
            if not isinstance(options, list) or len(options) < 2:
                raise serializers.ValidationError(
                    f'Question {i + 1} must have at least 2 options.',
                )
            for j, opt in enumerate(options):
                if not isinstance(opt, dict):
                    raise serializers.ValidationError(
                        f'Question {i + 1}, option {j + 1} must be an object.',
                    )
                if not isinstance(opt.get('text', ''), str):
                    raise serializers.ValidationError(
                        f'Question {i + 1}, option {j + 1} must have a string "text" field.',
                    )
                if not isinstance(opt.get('is_correct', False), bool):
                    raise serializers.ValidationError(
                        f'Question {i + 1}, option {j + 1} "is_correct" must be a boolean.',
                    )
        return value


class LessonLearnDetailSerializer(serializers.ModelSerializer):
    """Learner-facing lesson serializer — strips is_correct from quiz options."""
    quiz_data = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'description', 'lesson_type',
            'content', 'quiz_data', 'duration_minutes', 'order', 'is_required',
        ]

    def get_quiz_data(self, obj):
        return [
            {
                'question': q.get('question', ''),
                'options': [{'text': opt.get('text', '')} for opt in q.get('options', [])],
            }
            for q in (obj.quiz_data or [])
        ]


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'duration_minutes']


class ModuleWithLessonsSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'duration_minutes', 'lessons']


class LessonLearnSerializer(serializers.ModelSerializer):
    """Lightweight serializer for lesson sidebar — includes per-user completion flag."""
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'lesson_type', 'duration_minutes', 'order', 'is_completed']

    def get_is_completed(self, obj):
        return obj.id in self.context.get('completed_lesson_ids', set())


class ModuleLearnSerializer(serializers.ModelSerializer):
    lessons = LessonLearnSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'title', 'order', 'lessons']
