from typing import Dict

def read_topics(file_name = 'topics.txt') -> list:
    """Read topics from topics.txt file."""
    try:
        path = "input/"
        file_path = path + file_name
        # print(file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read lines and remove empty lines and whitespace
            topics = [line.strip() for line in f if line.strip()]
        return topics
    except FileNotFoundError:
        print("Warning: topics.txt not found. Using empty topics list.")
        return []
    except Exception as e:
        print(f"Error reading topics.txt: {e}")
        return []


def read_queries(file_name = 'queries.txt') -> Dict[str, str]:
    """Read and parse queries from queries.txt file."""
    try:
        path = "input/"
        file_path = path + file_name
        queries = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                # Split on first '=' only
                if '=' in line:
                    key, value = line.split('=', 1)
                    queries[key.strip()] = value.strip()
        return queries
    except FileNotFoundError:
        print("Warning: queries.txt not found. Using empty dictionary.")
        return {}
    except Exception as e:
        print(f"Error reading queries.txt: {e}")
        return {}

# todo: add more topics to search for
topics = read_topics()
queries = read_queries()


if __name__ == "__main__":
    print("topics and queries reader")
    print(type(topics), topics)
    print(type(queries), queries)