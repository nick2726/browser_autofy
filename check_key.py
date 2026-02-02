import os
from dotenv import load_dotenv

# 1. Load the .env file
load_dotenv()

# 2. Get the key
key = os.getenv("GOOGLE_API_KEY")

# 3. Check and print (masked for safety)
if key:
    masked_key = key[:5] + "..." + key[-5:]
    print(f"✅ Success! Key found: {masked_key}")
    
    # Optional: Check for common copy-paste errors
    if " " in key:
        print("⚠️ Warning: Your key contains spaces. Please check your .env file.")
    if key.startswith('"') or key.startswith("'"):
        print("⚠️ Warning: Your key starts with quotes. Remove them in the .env file.")
else:
    print("❌ Error: GOOGLE_API_KEY not found. Check your .env file name and location.")