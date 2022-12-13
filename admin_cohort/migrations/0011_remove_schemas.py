import os

from django.db import connection, migrations

db_owner = os.environ.get('DB_AUTH_USER')


def move_tables_to_public_schema(apps, schema_editor):
    with connection.cursor() as cr:
        q = """ SELECT table_schema, table_name FROM information_schema.tables
                WHERE table_type='BASE TABLE' AND table_schema NOT IN ('public', 'information_schema', 'pg_catalog')
                ORDER BY table_schema, table_name;
            """
        cr.execute(q)
        for i in cr.fetchall():
            q_alter_table = f"ALTER TABLE {i[0]}.{i[1]} SET SCHEMA public;"
            cr.execute(q_alter_table)


def move_sequences_to_public_schema(apps, schema_editor):
    with connection.cursor() as cr:
        q = """ SELECT sequence_schema, sequence_name FROM information_schema.sequences
                WHERE sequence_schema NOT IN ('public', 'information_schema', 'pg_catalog')
                ORDER BY sequence_schema, sequence_name;
            """
        cr.execute(q)
        for i in cr.fetchall():
            q_alter_sequence = f"ALTER SEQUENCE {i[0]}.{i[1]} SET SCHEMA public;"
            cr.execute(q_alter_sequence)


class Migration(migrations.Migration):
    """ change ownership of the public schema to db owner was done manually with Julien
        this mig does the following:
            1. move all tables from custom schemas to public
            2. move all sequences from custom schemas to public
            3. move all indexes from custom schemas to public
            4. drop custom schemas
    """
    dependencies = [('admin_cohort', '0010_delete_provider')]

    operations = [migrations.RunPython(code=move_tables_to_public_schema),
                  migrations.RunPython(code=move_sequences_to_public_schema),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS accesses;"),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS cohort;"),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS job_requests;"),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS job_request;"),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS environments;"),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS workspaces;")]
