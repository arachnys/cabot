SOURCE_CHANGED_EXISTING = 'The Grafana data source has changed from "{{ old_source }}" to "{{ new_source }}".'

SOURCE_CHANGED_NONEXISTING = SOURCE_CHANGED_EXISTING + ' The new source is not configured in Cabot, so the status ' \
                                                       'check will continue to use the old source.'

SERIES_CHANGED = 'The panel series ids have changed from {{ old_series }} to {{ new_series }}. ' \
                 'The check has not been changed.'

ES_QUERIES_CHANGED = "The queries have changed from:\n\n{% autoescape off %}{{ old_queries }}\n\nto:\n\n" \
                     "{{ new_queries }}\n\nDiff:\n{{ queries_diff }}{% endautoescape %}"
