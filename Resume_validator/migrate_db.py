import sqlite3

connection = sqlite3.connect("ats_business.db")

connection.execute(
    """
    ALTER TABLE evaluationrun
    ADD COLUMN user_facing_error TEXT
    """
)

connection.commit()
connection.close()

print("Migration completed.")