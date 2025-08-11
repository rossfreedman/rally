
INTEGRATION INSTRUCTIONS:
=========================

1. Add to import_players.py:
   ```python
   from data.etl.database_import.cnswpl_validation import validate_cnswpl_player_id_format
   
   # In load_players_data method, after loading data:
   if not validate_cnswpl_player_id_format(players_data):
       logger.error("❌ CNSWPL player ID validation failed")
       logger.error("❌ Stopping import to prevent match import failures")
       raise ValueError("CNSWPL player ID format validation failed")
   ```

2. Add to master_import.py before "Import Match Scores":
   ```python
   # Validate CNSWPL consistency before match import
   logger.info("🔍 Validating CNSWPL data consistency...")
   cnswpl_validation_result = subprocess.run([
       "python3", "data/etl/database_import/cnswpl_validation.py"
   ], capture_output=True, text=True)
   
   if cnswpl_validation_result.returncode != 0:
       logger.error("❌ CNSWPL validation failed - skipping match import")
       raise Exception("CNSWPL data validation failed")
   ```

3. Test the validation:
   ```bash
   python3 data/etl/database_import/cnswpl_validation.py
   ```
