from db_tools import get_database_schema

if __name__ == "__main__":
    print("🔍 TEST get_database_schema()\n")

    schema = get_database_schema.run()

    print("📋 SCHEMA:\n")
    print(schema)