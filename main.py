import sqlite3
import requests
import os

DB_PATH = "pokemon.db"

def create_database(DB_PATH): 
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon (
            id INTEGER PRIMARY KEY,
            name TEXT,
            height INTEGER,
            weight INTEGER,
            male_percentage REAL,
            female_percentage REAL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS type (
            name TEXT PRIMARY KEY
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ability (
            name TEXT PRIMARY KEY
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_type (
            pokemon_id INTEGER,
            type_name TEXT,
            PRIMARY KEY (pokemon_id, type_name),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
            FOREIGN KEY (type_name) REFERENCES type(name)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_ability (
            pokemon_id INTEGER,
            ability_name TEXT,
            PRIMARY KEY (pokemon_id, ability_name),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
            FOREIGN KEY (ability_name) REFERENCES ability(name)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            pokemon_id INTEGER,
            stat_name TEXT,
            base_stat INTEGER,
            PRIMARY KEY (pokemon_id, stat_name),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evolutions (
            pokemon_id INTEGER,
            evolves_to_id INTEGER,
            min_level INTEGER,
            trigger TEXT,
            item TEXT,
            PRIMARY KEY (pokemon_id, evolves_to_id),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
            FOREIGN KEY (evolves_to_id) REFERENCES pokemon(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS held_item (
            name TEXT PRIMARY KEY
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_held_item (
            pokemon_id INTEGER,
            item_name TEXT,
            PRIMARY KEY (pokemon_id, item_name),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
            FOREIGN KEY (item_name) REFERENCES held_item(name)
        )
        """)

        conn.commit()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()
            print(f"Database and tables created at '{DB_PATH}'")


def add_pokemon_to_db(DB_PATH, pokemon_id):
    """
    Fetch Pokémon data from the PokeAPI and insert it into the SQLite database.

    Args:
        db_path (str): File path to the SQLite database.
        pokemon_id (int): ID of the Pokémon to fetch and insert.

    Returns:
        None

    Raises:
        requests.RequestException: If the API request fails.
        sqlite3.Error: If an error occurs during SQLite database operations.
    """

    # Fetch Pokémon data from PokeAPI
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return
    
    try:
        data = response.json()
    except ValueError as e:
        print(f"Failed to decode JSON for Pokémon ID {pokemon_id}: {e}")
        return
    
    # Extract Basic Pokémon Information
    poke_id = data["id"]
    name = data["name"]
    height = data["height"]
    weight = data["weight"]

    # Extract Types, Abilities, Stats, and Held Items
    types = [t["type"]["name"] for t in data["types"]]
    abilities = [a["ability"]["name"] for a in data["abilities"]]
    stats = data["stats"]
    held_items = [item["item"]["name"] for item in data.get("held_items", [])]

    #Extract Species data
    species_url = data["species"]["url"]
    try:
        species_res = requests.get(species_url, timeout=5)
        species_res.raise_for_status()
        species_data = species_res.json()
    except requests.RequestException as e:
        print(f"Failed to fetch species data for Pokémon ID {pokemon_id}: {e}")
        return
      
    evo_chain_url = species_data["evolution_chain"]["url"]

    # Get gender rate and convert to male/female percentages
    gender_rate = species_data.get("gender_rate", -1)
    if gender_rate == -1:
        male_pct = female_pct = None
    else:
        female_pct = gender_rate * 12.5
        male_pct = 100 - female_pct

    # Fetch evolution chain data to map evolutions
    try:
        evo_res = requests.get(evo_chain_url, timeout=5)
        evo_res.raise_for_status()
        evo_data = evo_res.json()["chain"]
    except requests.RequestException as e:
        print(f"Failed to fetch evolution chain for Pokémon ID {pokemon_id}: {e}")
        return


    def parse_chain(chain, evolutions_list):
        """
        Recursively parse the evolution chain and collect evolutions.

        Args:
            chain (dict): The current evolution chain node.
            evolutions_list (list): List to collect evolution tuples.

        Returns:
            None            
        """
        from_name = chain["species"]["name"]
        evolves_to = chain["evolves_to"]
        for evo in evolves_to:
            to_name = evo["species"]["name"]
            details = evo.get("evolution_details", [])
            evolutions_list.append((from_name, to_name, details))
            parse_chain(evo, evolutions_list)

    # Parse the evolution chain
    evolutions = []
    parse_chain(evo_data, evolutions)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Insert basic Pokémon info
        cursor.execute("""
            INSERT OR REPLACE INTO pokemon (id, name, height, weight)
            VALUES (?, ?, ?, ?)
        """, (poke_id, name, height, weight))

        # Update gender info directly in the Pokémon table
        cursor.execute("""
            UPDATE pokemon
            SET male_percentage = ?, female_percentage = ?
            WHERE id = ?
        """, (male_pct, female_pct, poke_id))


        # Insert each type into 'type' table and link to Pokémon
        for t in types:
            cursor.execute("INSERT OR IGNORE INTO type (name) VALUES (?)", (t,))
            cursor.execute("INSERT OR IGNORE INTO pokemon_type (pokemon_id, type_name) VALUES (?, ?)", (poke_id, t))

        # Insert each abilities into 'ability' table and link to Pokémon
        for a in abilities:
            cursor.execute("INSERT OR IGNORE INTO ability (name) VALUES (?)", (a,))
            cursor.execute("INSERT OR IGNORE INTO pokemon_ability (pokemon_id, ability_name) VALUES (?, ?)", (poke_id, a))

        # Insert stats
        for stat in stats:
            stat_name = stat["stat"]["name"]
            base_stat = stat["base_stat"]
            cursor.execute("""
                INSERT OR REPLACE INTO stats (pokemon_id, stat_name, base_stat)
                VALUES (?, ?, ?)
            """, (poke_id, stat_name, base_stat))

        # Insert held items
        for item_name in held_items:
            cursor.execute("INSERT OR IGNORE INTO held_item (name) VALUES (?)", (item_name,))
            cursor.execute("INSERT OR IGNORE INTO pokemon_held_item (pokemon_id, item_name) VALUES (?, ?)", (poke_id, item_name))

        # Insert evolutions (only if both from and to exist in DB)
        for from_name, to_name, details_list in evolutions:
            cursor.execute("SELECT id FROM pokemon WHERE name = ?", (from_name,))
            from_result = cursor.fetchone()
            cursor.execute("SELECT id FROM pokemon WHERE name = ?", (to_name,))
            to_result = cursor.fetchone()

            if from_result and to_result:
                from_id = from_result[0]
                to_id = to_result[0]
                for detail in details_list:
                    min_level = detail.get("min_level")
                    trigger = detail["trigger"]["name"] if detail.get("trigger") else None
                    item = detail["item"]["name"] if detail.get("item") else None
                    cursor.execute("""
                        INSERT OR IGNORE INTO evolutions (pokemon_id, evolves_to_id, min_level, trigger, item)
                        VALUES (?, ?, ?, ?, ?)
                    """, (from_id, to_id, min_level, trigger, item))

        conn.commit()
        print(f"Inserted Pokémon {name.capitalize()} (ID {poke_id})")       #For demonstration purposes
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()
    
    

def read_single_pokemon_data(DB_PATH, pokemon_id):
    """
    Retrieve and display data for a single Pokémon from the SQLite database.

    Args:
        db_path (str): File path to the SQLite database.
        pokemon_id (int): ID of the Pokémon to read.

    Returns:
        None

    Raises:
        sqlite3.Error: If an error occurs during SQLite database operations.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Connect to the database and fetch basic Pokémon info
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, height, weight FROM pokemon WHERE id = ?", (pokemon_id,))
            poke = cursor.fetchone()

            if not poke:
                print(f"No Pokémon found with ID {pokemon_id}")
                return 

            poke_id, name, height, weight = poke
            print(f"ID: {poke_id}, Name: {name.capitalize()}, Height: {height}, Weight: {weight}")

            # Fetch and display Pokémon types
            cursor.execute("SELECT type_name FROM pokemon_type WHERE pokemon_id = ?", (poke_id,))
            types = [row[0] for row in cursor.fetchall()]
            print("Types:", ", ".join(types) if types else "None")

            # Fetch and display Pokémon abilities
            cursor.execute("SELECT ability_name FROM pokemon_ability WHERE pokemon_id = ?", (poke_id,))
            abilities = [row[0] for row in cursor.fetchall()]
            print("Abilities:", ", ".join(abilities) if abilities else "None")

            # Fetch and display Pokémon stats
            cursor.execute("SELECT stat_name, base_stat FROM stats WHERE pokemon_id = ?", (poke_id,))
            stats = cursor.fetchall()
            if stats:
                print("Stats:")
                for stat_name, base_stat in stats:
                    print(f"  {stat_name}: {base_stat}")
            else:
                print("Stats: None found")

            # Fetch and display gender information
            # Fetch and display gender information (now from the 'pokemon' table)
            cursor.execute("SELECT male_percentage, female_percentage FROM pokemon WHERE id = ?", (poke_id,))
            gender = cursor.fetchone()
            if gender:
                male_pct, female_pct = gender
                if male_pct is None and female_pct is None:
                    print("Gender: Genderless")
                else:
                    print(f"Gender: Male {male_pct}%, Female {female_pct}%")
            else:
                print("Gender: Unknown")

            # Fetch and display held items
            cursor.execute("SELECT item_name FROM pokemon_held_item WHERE pokemon_id = ?", (poke_id,))
            held_items = [row[0] for row in cursor.fetchall()]
            print("Held items:", ", ".join(held_items) if held_items else "None")

            # Fetch and display evolutions
            cursor.execute("""
                SELECT evolves_to_id, min_level, trigger, item
                FROM evolutions
                WHERE pokemon_id = ?
            """, (poke_id,))
            evolutions = cursor.fetchall()
            if evolutions:
                print("Evolves to:")
                for evo_id, min_level, trigger, item in evolutions:
                    cursor.execute("SELECT name FROM pokemon WHERE id = ?", (evo_id,))
                    evo_result = cursor.fetchone()
                    evo_name = evo_result[0].capitalize() if evo_result else f"ID {evo_id}"

                    evo_details = []
                    if min_level is not None:
                        evo_details.append(f"Level {min_level}")
                    if trigger:
                        evo_details.append(f"Trigger: {trigger}")
                    if item:
                        evo_details.append(f"Item: {item}")

                    print(f"  -> {evo_name} ({', '.join(evo_details)})")
            else:
                print("Evolves to: None")

            # Print a separator for better readability
            print("-" * 40)

    except sqlite3.Error as e:
        print(f"Database error occurred: {e}")


if __name__ == "__main__":
    pokemon_number = 151  # Total number of Pokémon in Gen 1 , easily adjustable for future generations
    # Check if database exists; if not, create and populate it
    if not os.path.exists(DB_PATH):
        print(f"The database file '{DB_PATH}' was not found. Creating database and loading Pokémon data...")
        try:
            create_database(DB_PATH)
            for i in range(1, pokemon_number+1):  
                add_pokemon_to_db(DB_PATH, i)
            print("Database created successfully.")
        except Exception as e:
            print(f"Error while creating or filling the database: {e}")
            exit(1)

    try:
        # Main interactive loop for user input
        while True:
            user_input = input("\nEnter a Pokémon ID (1–151) or 'exit' to quit: ").strip().lower()

            if user_input == "exit":
                print("Program terminated.")
                break
            elif user_input.isdigit():
                poke_id = int(user_input)
                if 1 <= poke_id <= pokemon_number:                  
                    read_single_pokemon_data(DB_PATH, poke_id)
                else:
                    print("Only Pokémon IDs from 1 to 151 are allowed.")
            else:
                print("Invalid input. Please enter a number from 1 to 151 or 'exit'.")
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")