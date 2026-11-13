"""Recover legacy databases whose initial migration was recorded without tenant tables."""
from django.db import migrations


def restore_missing_tables(apps, schema_editor):
    existing = set(schema_editor.connection.introspection.table_names())
    for name in ('BillingPlan', 'Tenant', 'TenantDomain'):
        model = apps.get_model('tenants', name)
        if model._meta.db_table not in existing:
            schema_editor.create_model(model)
            existing.add(model._meta.db_table)


class Migration(migrations.Migration):
    dependencies = [('tenants', '0001_initial')]
    operations = [migrations.RunPython(restore_missing_tables, migrations.RunPython.noop)]
