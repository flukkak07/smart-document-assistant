import os
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
        print("Nodes in DB:", nodes)
        
        # Check relationships
        rels = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count").data()
        print("Relationships in DB:", rels)
        
        # Check a sample relationship
        sample = session.run("MATCH (n)-[r]->(m) RETURN n.id, type(r), m.id LIMIT 5").data()
        print("Sample data:", sample)

try:
    check_data()
finally:
    driver.close()
