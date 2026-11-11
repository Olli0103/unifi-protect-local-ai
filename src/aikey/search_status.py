"""Bounded last-completed query observation, never a readiness or quality probe."""

KINDS = frozenset({'text', 'image'})
FAILURES = frozenset({'text_failed', 'image_failed', 'image_uri', 'image_fetch',
    'image_format', 'image_too_large', 'image_encoder',
    *(f'image_http_{n}xx' for n in range(1, 6))})


def last_query(search):
    if 'last_query' not in search:
        return None  # Older runtimes do not report a last outcome.
    value = search['last_query']
    if not isinstance(value, dict) or set(value) != {'kind', 'outcome', 'failure'}:
        raise ValueError('Invalid search query observation')
    if (not isinstance(value['outcome'], str)
            or value['kind'] is not None and not isinstance(value['kind'], str)
            or value['failure'] is not None and not isinstance(value['failure'], str)):
        raise ValueError('Invalid search query observation types')
    if value['outcome'] == 'not_observed':
        if value['kind'] is not None or value['failure'] is not None:
            raise ValueError('Invalid unobserved search query')
    elif (value['kind'] not in KINDS or value['outcome'] not in {'succeeded', 'failed'}
          or value['outcome'] == 'succeeded' and value['failure'] is not None
          or value['outcome'] == 'failed' and (value['failure'] not in FAILURES
              or not value['failure'].startswith(value['kind'] + '_'))):
        raise ValueError('Invalid search query outcome')
    return dict(value)


def record_query(status, kind, failure=None):
    value = {'kind': kind, 'outcome': 'failed' if failure else 'succeeded', 'failure': failure}
    status['last_query'] = last_query({'last_query': value})


def image_failure(category):
    values = {'uri': 'image_uri', 'fetch': 'image_fetch', 'format': 'image_format',
              'too_large': 'image_too_large', 'clip': 'image_encoder',
              **{f'http_{n}xx': f'image_http_{n}xx' for n in range(1, 6)}}
    return values.get(category, 'image_failed')
