# PokeETLCodingChallenge
This Python application addresses a data engineering challenge focused on the extraction, transformation, and loading of Pokémon data with help of the PokeAPI (https://pokeapi.co). 
It fetches detailed information for multiple Pokemon from the PokeAPI, transforms the nested JSON responses into a structured format, and loads the data into a relational SQLite database.
Users can then query and explore various Pokémon attributes, such as types, abilities, stats, and evolution chains, via a command-line interface.
If the SQLite database file does not exist, it will be created and automatically populated with data for the first 151 Pokemon.
The user can easily change the code to create a table with the first x Pokemon; for demonstration purposes only, the first 151 Pokemon are loaded.


You can run the solution it either directly on your system using Python or via Docker. Below are both methods:

Option 1: Run Locally with Python
1. Clone the Repository:
    git clone https://github.com/nV153/PokeETLCodingChallenge/tree/main
    cd PokeETLCodingChallenge
2. Install Dependencies:
    pip install -r requirements.txt
3. Run the Application:
    python main.py

Option 2: Run with Docker
1. Build the Docker Image
    docker build -t pokecodingchallenge .
2. Run the Container
    docker run -it pokecodingchallenge



DESIGN CHOICES:
This project follows a classic ETL (Extract, Transform, Load) structure.
Since the JSON responses returned by the PokeAPI are nested and vary in structure, it is important to identify and flatten the relevant pieces of information in a consistent and normalized way suitable for relational storage.
The manner in which this project accomplishes this is shown in the Key Mapping Overview.

Key Mapping Overview:
Basic Info (name, height, weight) → Stored in table: 'pokemon'
Types (types[].type.name) → Stored in tables: 'type' and linking table 'pokemon_type' (many-to-many)
Abilities (abilities[].ability.name) → Stored in tables: 'ability' and 'pokemon_ability' (many-to-many)
Stats (stats[].stat.name and base_stat) → Stored in table: 'stats' (one row per stat per Pokemon)
Held Items (held_items[].item.name) → Stored in tables: 'held_item' and 'pokemon_held_item' (optional, many-to-many)
Gender Rate (species.gender_rate) → Transformed into male and female percentages, stored in table: 'gender'
Evolution Chain (evolution_chain.chain) → Recursively parsed and stored in table: 'evolutions' with from_id → to_id and optional trigger, level, or item

The schema is normalized to avoid redundancy.
Many-to-many relationships (e.g., Pokemon to Types, Abilities) are implemented via linking tables.
All data is indexed using the Pokemon to optimize lookup performance.
Tables are related via foreign keys to allow meaningful joins (e.g., list all Pokemon with a certain ability).
This approach tries to create clean, structured data storage that can scale easily and support analytical queries.

ASSUMPTIONS:
The data loaded from the Pokemon API is correct and available when creating the database.
Missing evolutions are skipped, meaning evolution entries are only inserted into the database if both the source and target Pokemon are already present. Otherwise, the relationship is ignored. This is only relevant for Pokemon whose evolution has a significant number gap and if not all Pokemon are loaded into the database.
When the Pokemon gender rate is -1, the Pokemon is treated as genderless. This is stored in the database as 'NULL' for both the male and female percentages.

