"""Check evidence linkage, not originality scores or AdSense eligibility."""
from datetime import date

POLICY_START = date(2026, 9, 29)


def reader_value_reasons(source, identity):
    if date.fromisoformat(identity.publish_date) < POLICY_START:
        return []
    editorial = source.get('editorial')
    review = editorial.get('value_review') if isinstance(editorial, dict) else None
    if not isinstance(review, dict):
        return ['quality_value_review']
    for key in ('primary_reader', 'reader_question', 'source_gap', 'selection_reason'):
        if not isinstance(review.get(key), str) or not review[key].strip():
            return ['quality_value_review']
    # Only visible prose counts. A claim in metadata or image prompt is not proof.
    prose, urls = [], set()
    articles = source.get('news')
    if not isinstance(articles, list):
        return ['quality_value_review']
    for article in articles:
        if not isinstance(article, dict):
            return ['quality_value_review']
        references, blocks = article.get('references'), article.get('content')
        if not isinstance(references, list) or not isinstance(blocks, list):
            return ['quality_value_review']
        for reference in references:
            if isinstance(reference, dict):
                url = reference.get('url')
                if isinstance(url, str) and url.startswith('https://'):
                    urls.add(url)
        for block in blocks:
            if not isinstance(block, dict):
                return ['quality_value_review']
            if block.get('t') in ('p', 'quote') and isinstance(block.get('text'), str):
                prose.append(block['text'])
            if block.get('t') == 'ul':
                prose.extend(v for v in block.get('items', []) if isinstance(v, str))
    def visible(value):
        return isinstance(value, str) and len(value.strip()) >= 12 and any(value in p for p in prose)
    contributions = review.get('contributions')
    if not isinstance(contributions, list) or not contributions:
        return ['quality_value_review']
    for item in contributions:
        if not isinstance(item, dict) or item.get('basis') not in ('documented', 'observed', 'inference'):
            return ['quality_value_review']
        if not visible(item.get('excerpt')) or not visible(item.get('limit_excerpt')):
            return ['quality_value_review']
        evidence = item.get('source_urls')
        if not isinstance(evidence, list) or not evidence or any(not isinstance(u, str) or u not in urls for u in evidence):
            return ['quality_value_review']
        # Claims of personal testing need a traceable artifact, never a generated image.
        if item['basis'] == 'observed':
            record = item.get('observation_record')
            if not isinstance(record, str) or not record.strip():
                return ['quality_value_review']
        if item['basis'] == 'inference' and not visible(item.get('disclosure_excerpt')):
            return ['quality_value_review']
    return []
