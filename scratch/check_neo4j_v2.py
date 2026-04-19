import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USERNAME", "neo4j")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

def check_data():
    with driver.session() as session:
        # Check nodes
        nodes = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count").data()
        
        # Check relationships
        rels = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count").data()
        
        # Check a sample relationship
        sample = session.run("MATCH (n)-[r]->(m) RETURN properties(n) as n, type(r) as rel, properties(m) as m LIMIT 5").data()
        
        result = {
            "node_stats": nodes,
            "rel_stats": rels,
            "sample": sample
        }
        # Print as JSON for safe encoding
        print(json.dumps(result, ensure_ascii=False))

try:
    check_data()
except Exception as e:
    print(f"Error: {e}")
finally:
    driver.close()
