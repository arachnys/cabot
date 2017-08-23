from django.db import models


class PositiveIntegerMaxField(models.PositiveIntegerField):

    def __init__(self, verbose_name=None, name=None, max_value=None, **kwargs):
        self.max_value = max_value
        models.PositiveIntegerField.__init__(self, verbose_name, name, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'max_value': self.max_value}
        defaults.update(kwargs)
        return super(PositiveIntegerMaxField, self).formfield(**defaults)

    def south_field_triple(self):
        """
        South cannot introspect custom fields, so we must add this as an
        introspection rule to be able to run the schema migration
        """
        try:
            from south.modelsinspector import introspector
            cls_name = '{0}.{1}'.format(
                self.__class__.__module__,
                self.__class__.__name__)
            args, kwargs = introspector(self)
            return cls_name, args, kwargs
        except ImportError:
            pass
