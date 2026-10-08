from rest_framework import serializers

from hub.models import Activity, Module, Resource

from .localize import localized, viewer_language

MEDIA_ITEM_TYPES = {'image', 'video', 'pdf'}


class ResourceSerializer(serializers.ModelSerializer):
    """Authoring view of one resource block within an activity."""
    h5p_packages = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = [
            'id', 'type', 'order', 'is_required', 'title', 'content', 'url',
            'caption', 'quiz_data', 'instructions', 'translations',
            'h5p_self_complete', 'h5p_packages',
        ]
        read_only_fields = ['translations']

    def validate_quiz_data(self, value):
        return LessonSerializer().validate_quiz_data(value)

    def get_h5p_packages(self, obj):
        if obj.type != Resource.Type.H5P:
            return []
        return [
            {
                'id': p.id, 'language': p.language, 'title': p.title,
                'main_library': p.main_library, 'size_bytes': p.size_bytes,
                'version': p.version, 'path': p.media_path, 'uploaded_at': p.uploaded_at,
            }
            for p in obj.h5p_packages.all()
        ]


class ResourceLearnSerializer(serializers.ModelSerializer):
    """Learner view of a resource — localized, with quiz answers stripped."""
    content = serializers.SerializerMethodField()
    caption = serializers.SerializerMethodField()
    instructions = serializers.SerializerMethodField()
    quiz_data = serializers.SerializerMethodField()
    h5p = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = [
            'id', 'type', 'order', 'is_required', 'title', 'content', 'url',
            'caption', 'quiz_data', 'instructions', 'h5p_self_complete', 'h5p',
        ]

    def get_h5p(self, obj):
        """The package to play: the viewer's language version, else the main file."""
        if obj.type != Resource.Type.H5P:
            return None
        packages = {p.language: p for p in obj.h5p_packages.all()}
        package = packages.get(viewer_language(self.context)) or packages.get('')
        if package is None:
            return None
        return {
            'package_id': package.id, 'path': package.media_path, 'language': package.language,
            'version': package.version, 'title': package.title, 'main_library': package.main_library,
        }

    def get_content(self, obj):
        return localized(obj, 'content', viewer_language(self.context))

    def get_caption(self, obj):
        return localized(obj, 'caption', viewer_language(self.context))

    def get_instructions(self, obj):
        return localized(obj, 'instructions', viewer_language(self.context))

    def get_quiz_data(self, obj):
        quiz_data = localized(obj, 'quiz_data', viewer_language(self.context))
        return [
            {
                'question': q.get('question', ''),
                'options': [{'text': opt.get('text', '')} for opt in q.get('options', [])],
            }
            for q in (quiz_data or [])
        ]


class LessonSerializer(serializers.ModelSerializer):
    resources = ResourceSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'description', 'lesson_type',
            'content', 'media_items', 'quiz_data', 'duration_minutes', 'order', 'is_required',
            'translations', 'resources',
        ]
        read_only_fields = ['translations']

    def validate_media_items(self, value):
        """An ordered list of blocks: a text block {type: 'text', html: str} or a
        media block {type: image|video|pdf, url: str, caption: str}."""
        if not isinstance(value, list):
            raise serializers.ValidationError('media_items must be a list.')
        cleaned = []
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f'Block {i + 1} must be an object.')
            item_type = item.get('type')
            if item_type == 'text':
                cleaned.append({'type': 'text', 'html': str(item.get('html', ''))})
            elif item_type in MEDIA_ITEM_TYPES:
                url = str(item.get('url', '')).strip()
                if not url:
                    raise serializers.ValidationError(f'Block {i + 1} needs a url.')
                cleaned.append({'type': item_type, 'url': url, 'caption': str(item.get('caption', ''))})
            else:
                raise serializers.ValidationError(
                    f"Block {i + 1} type must be 'text' or one of {sorted(MEDIA_ITEM_TYPES)}.",
                )
        return cleaned

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
    """Learner-facing lesson serializer — resolves to the viewer's language
    (falling back to the original) and strips is_correct from quiz options."""
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    quiz_data = serializers.SerializerMethodField()
    resources = ResourceLearnSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'description', 'lesson_type',
            'content', 'media_items', 'quiz_data', 'duration_minutes', 'order', 'is_required',
            'resources',
        ]

    def get_title(self, obj):
        return localized(obj, 'title', viewer_language(self.context))

    def get_description(self, obj):
        return localized(obj, 'description', viewer_language(self.context))

    def get_content(self, obj):
        return localized(obj, 'content', viewer_language(self.context))

    def get_quiz_data(self, obj):
        quiz_data = localized(obj, 'quiz_data', viewer_language(self.context))
        return [
            {
                'question': q.get('question', ''),
                'options': [{'text': opt.get('text', '')} for opt in q.get('options', [])],
            }
            for q in (quiz_data or [])
        ]


class ModuleSerializer(serializers.ModelSerializer):
    """Shared by the learner-facing CourseDetailSerializer and the authoring
    endpoints — deliberately does NOT expose the raw `translations` blob
    (learners only ever see fields resolved to their language)."""

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'duration_minutes', 'related_outcomes']

    def validate_related_outcomes(self, value):
        """Indices into the course's learning outcomes; de-duplicated, sorted."""
        if not isinstance(value, list) or not all(
            isinstance(i, int) and not isinstance(i, bool) and i >= 0 for i in value
        ):
            raise serializers.ValidationError('related_outcomes must be a list of outcome indices.')
        return sorted(set(value))


class ModuleAuthoringSerializer(ModuleSerializer):
    """Authoring variant of ModuleSerializer — exposes the raw translations
    blob for the course/module editor payloads."""

    class Meta(ModuleSerializer.Meta):
        fields = [*ModuleSerializer.Meta.fields, 'translations']
        read_only_fields = ['translations']


class ModuleLocalizedSerializer(serializers.ModelSerializer):
    """Learner-facing module — title/description resolved to the viewer's
    language with fallback to the original (used by CourseDetailSerializer)."""
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'duration_minutes', 'related_outcomes']

    def get_title(self, obj):
        from .localize import localized, viewer_language
        return localized(obj, 'title', viewer_language(self.context))

    def get_description(self, obj):
        from .localize import localized, viewer_language
        return localized(obj, 'description', viewer_language(self.context))


class ModuleWithLessonsSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = [
            'id', 'title', 'description', 'order', 'duration_minutes', 'lessons', 'translations',
        ]
        read_only_fields = ['translations']


class LessonLearnSerializer(serializers.ModelSerializer):
    """Lightweight serializer for lesson sidebar — includes per-user completion flag."""
    title = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    resource_types = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'lesson_type', 'duration_minutes', 'order', 'is_completed',
            'resource_types',
        ]

    def get_title(self, obj):
        return localized(obj, 'title', viewer_language(self.context))

    def get_is_completed(self, obj):
        return obj.id in self.context.get('completed_lesson_ids', set())

    def get_resource_types(self, obj):
        # Ordered and de-duplicated; drives the sidebar icon.
        types = [r.type for r in sorted(obj.resources.all(), key=lambda r: r.order)]
        return list(dict.fromkeys(types))


class ModuleLearnSerializer(serializers.ModelSerializer):
    lessons = LessonLearnSerializer(many=True, read_only=True)
    title = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ['id', 'title', 'order', 'lessons']

    def get_title(self, obj):
        return localized(obj, 'title', viewer_language(self.context))
