def get_related_translation_annotation_name(related_name, language_code):
    return f"{related_name}_{language_code.replace('-', '_')}"