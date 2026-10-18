"""
Opportunity Database
-------------------
Module that handles storing and retrieving opportunity data from SQLite database.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Set

logger = logging.getLogger("opportunity_database")

class OpportunityDatabase:
    """Manages the storage and retrieval of opportunity data."""
    
    def __init__(self, db_path: str = "data/opportunities.db"):
        """Initialize the database connection."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Initialize tables if they don't exist
        self._initialize_tables()
        
        logger.info(f"Initialized database at {db_path}")
    
    def _initialize_tables(self):
        """Create necessary tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Create opportunities table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            category TEXT,
            value_amount REAL,
            value_currency TEXT,
            location TEXT,
            status TEXT,
            closing_date TEXT,
            publishing_date TEXT,
            agency TEXT,
            contact_name TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            url TEXT,
            source TEXT,
            panel_data TEXT,
            scope TEXT,
            market_timing TEXT,
            capital_value TEXT,
            is_public INTEGER DEFAULT 1,
            last_updated TEXT,
            raw_data TEXT
        )
        ''')
        
        # Create tags table for advanced filtering
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS opportunity_tags (
            opportunity_id TEXT,
            tag TEXT,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities(id),
            PRIMARY KEY (opportunity_id, tag)
        )
        ''')
        
        # Create table for documents associated with opportunities
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS opportunity_documents (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT,
            title TEXT,
            description TEXT,
            url TEXT,
            file_type TEXT,
            file_size INTEGER,
            published_date TEXT,
            is_downloaded INTEGER DEFAULT 0,
            local_path TEXT,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
        )
        ''')
        
        # Create index for faster searching
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_opp_category ON opportunities(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunities(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_opp_source ON opportunities(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_opp_closing_date ON opportunities(closing_date)')
        
        self.conn.commit()
        logger.info("Database tables initialized")
    
    def add_or_update_opportunity(self, opportunity_data: Dict) -> bool:
        """
        Add a new opportunity or update an existing one.
        
        Args:
            opportunity_data: Dictionary containing opportunity details
            
        Returns:
            bool: True if this is a new opportunity, False if updated
        """
        cursor = self.conn.cursor()
        
        # Check if opportunity already exists
        opp_id = opportunity_data.get("id", "")
        cursor.execute("SELECT id FROM opportunities WHERE id = ?", (opp_id,))
        existing = cursor.fetchone()
        
        # Extract standard fields (defined in schema)
        standard_fields = {
            "id": opportunity_data.get("id", ""),
            "title": opportunity_data.get("title", ""),
            "description": opportunity_data.get("description", ""),
            "category": opportunity_data.get("category", ""),
            "value_amount": opportunity_data.get("value_amount"),
            "value_currency": opportunity_data.get("value_currency", "AUD"),
            "location": opportunity_data.get("location", ""),
            "status": opportunity_data.get("status", ""),
            "closing_date": opportunity_data.get("closing_date", ""),
            "publishing_date": opportunity_data.get("publishing_date", ""),
            "agency": opportunity_data.get("agency", ""),
            "contact_name": opportunity_data.get("contact_name", ""),
            "contact_email": opportunity_data.get("contact_email", ""),
            "contact_phone": opportunity_data.get("contact_phone", ""),
            "url": opportunity_data.get("url", ""),
            "source": opportunity_data.get("source", ""),
            "panel_data": json.dumps(opportunity_data.get("panel_data", {})),
            "scope": opportunity_data.get("scope", ""),
            "market_timing": opportunity_data.get("market_timing", ""),
            "capital_value": opportunity_data.get("capital_value", ""),
            "is_public": opportunity_data.get("is_public", 1),
            "last_updated": datetime.now().isoformat(),
            "raw_data": json.dumps(opportunity_data)
        }
        
        # Store any tags
        tags = opportunity_data.get("tags", [])
        
        # Store documents
        documents = opportunity_data.get("documents", [])
        
        if existing:
            # Update existing record
            placeholders = ", ".join([f"{k} = ?" for k in standard_fields.keys()])
            query = f"UPDATE opportunities SET {placeholders} WHERE id = ?"
            values = list(standard_fields.values()) + [opp_id]
            cursor.execute(query, values)
            
            # Delete existing tags and re-add
            cursor.execute("DELETE FROM opportunity_tags WHERE opportunity_id = ?", (opp_id,))
            
            logger.info(f"Updated opportunity {opp_id}")
            is_new = False
        else:
            # Insert new record
            placeholders = ", ".join(["?"] * len(standard_fields))
            fields = ", ".join(standard_fields.keys())
            query = f"INSERT INTO opportunities ({fields}) VALUES ({placeholders})"
            cursor.execute(query, list(standard_fields.values()))
            
            logger.info(f"Added new opportunity {opp_id}")
            is_new = True
        
        # Add tags
        for tag in tags:
            cursor.execute("INSERT OR IGNORE INTO opportunity_tags (opportunity_id, tag) VALUES (?, ?)",
                          (opp_id, tag))
        
        # Add documents
        for doc in documents:
            doc_id = doc.get("id", f"{opp_id}_{hash(doc.get('url', ''))}")
            cursor.execute("""
            INSERT OR REPLACE INTO opportunity_documents 
            (id, opportunity_id, title, description, url, file_type, file_size, published_date, is_downloaded, local_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                opp_id,
                doc.get("title", ""),
                doc.get("description", ""),
                doc.get("url", ""),
                doc.get("file_type", ""),
                doc.get("file_size", 0),
                doc.get("published_date", ""),
                doc.get("is_downloaded", 0),
                doc.get("local_path", "")
            ))
        
        self.conn.commit()
        return is_new
    
    def get_opportunity(self, opportunity_id: str) -> Dict:
        """Get a single opportunity by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
        row = cursor.fetchone()
        
        if not row:
            return {}
        
        opportunity = dict(row)
        
        # Get tags
        cursor.execute("SELECT tag FROM opportunity_tags WHERE opportunity_id = ?", (opportunity_id,))
        tags = [row["tag"] for row in cursor.fetchall()]
        opportunity["tags"] = tags
        
        # Get documents
        cursor.execute("SELECT * FROM opportunity_documents WHERE opportunity_id = ?", (opportunity_id,))
        documents = [dict(row) for row in cursor.fetchall()]
        opportunity["documents"] = documents
        
        # Parse JSON fields
        if "panel_data" in opportunity and opportunity["panel_data"]:
            try:
                opportunity["panel_data"] = json.loads(opportunity["panel_data"])
            except:
                opportunity["panel_data"] = {}
        
        if "raw_data" in opportunity and opportunity["raw_data"]:
            try:
                opportunity["raw_data"] = json.loads(opportunity["raw_data"])
            except:
                opportunity["raw_data"] = {}
        
        return opportunity
    
    def search_opportunities(self, 
                           query: str = None,
                           category: str = None,
                           source: str = None,
                           status: str = None,
                           min_value: float = None,
                           max_value: float = None,
                           tags: List[str] = None,
                           closing_after: str = None,
                           limit: int = 100,
                           offset: int = 0) -> List[Dict]:
        """
        Search for opportunities with various filters.
        
        Args:
            query: Text search in title and description
            category: Filter by category
            source: Filter by source website
            status: Filter by status
            min_value, max_value: Filter by value range
            tags: Filter by tags (must have all tags)
            closing_after: Only opportunities closing after this date (ISO format)
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of matching opportunities
        """
        cursor = self.conn.cursor()
        
        conditions = ["1=1"]  # Always true condition to simplify query building
        params = []
        
        # Add conditions based on parameters
        if query:
            conditions.append("(title LIKE ? OR description LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        if source:
            conditions.append("source = ?")
            params.append(source)
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if min_value is not None:
            conditions.append("value_amount >= ?")
            params.append(min_value)
        
        if max_value is not None:
            conditions.append("value_amount <= ?")
            params.append(max_value)
        
        if closing_after:
            conditions.append("closing_date >= ?")
            params.append(closing_after)
        
        # Create the base query
        query_sql = f"""
        SELECT * FROM opportunities 
        WHERE {" AND ".join(conditions)}
        """
        
        # Handle tag filtering (requires subquery)
        if tags and len(tags) > 0:
            tags_placeholders = ", ".join(["?"] * len(tags))
            for tag in tags:
                query_sql += f"""
                AND id IN (
                    SELECT opportunity_id FROM opportunity_tags 
                    WHERE tag IN ({tags_placeholders})
                    GROUP BY opportunity_id
                    HAVING COUNT(DISTINCT tag) = ?
                )
                """
                params.extend(tags)
                params.append(len(tags))  # Ensure all tags are present
        
        # Add ordering and pagination
        query_sql += """
        ORDER BY closing_date DESC, last_updated DESC
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        cursor.execute(query_sql, params)
        opportunities = [dict(row) for row in cursor.fetchall()]
        
        # Get tags and parse JSON fields for each opportunity
        for opp in opportunities:
            opp_id = opp["id"]
            
            # Get tags
            cursor.execute("SELECT tag FROM opportunity_tags WHERE opportunity_id = ?", (opp_id,))
            tags = [row["tag"] for row in cursor.fetchall()]
            opp["tags"] = tags
            
            # Parse JSON fields
            if "panel_data" in opp and opp["panel_data"]:
                try:
                    opp["panel_data"] = json.loads(opp["panel_data"])
                except:
                    opp["panel_data"] = {}
            
            if "raw_data" in opp and opp["raw_data"]:
                try:
                    opp["raw_data"] = json.loads(opp["raw_data"])
                except:
                    opp["raw_data"] = {}
        
        return opportunities
    
    def get_recent_opportunities(self, 
                              limit: int = 10, 
                              hours: int = 24,
                              source: str = None) -> List[Dict]:
        """
        Get opportunities added or updated in the last X hours.
        
        Args:
            limit: Maximum number of results
            hours: Number of hours to look back
            source: Filter by source website
            
        Returns:
            List of recent opportunities
        """
        cursor = self.conn.cursor()
        
        # Calculate the cutoff time
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # Build the query
        query = "SELECT * FROM opportunities WHERE last_updated >= ?"
        params = [cutoff_time]
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        query += " ORDER BY last_updated DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        opportunities = [dict(row) for row in cursor.fetchall()]
        
        # Get tags and parse JSON fields for each opportunity
        for opp in opportunities:
            opp_id = opp["id"]
            
            # Get tags
            cursor.execute("SELECT tag FROM opportunity_tags WHERE opportunity_id = ?", (opp_id,))
            tags = [row["tag"] for row in cursor.fetchall()]
            opp["tags"] = tags
            
            # Parse JSON fields
            if "panel_data" in opp and opp["panel_data"]:
                try:
                    opp["panel_data"] = json.loads(opp["panel_data"])
                except:
                    opp["panel_data"] = {}
            
            if "raw_data" in opp and opp["raw_data"]:
                try:
                    opp["raw_data"] = json.loads(opp["raw_data"])
                except:
                    opp["raw_data"] = {}
        
        return opportunities
    
    def get_statistics(self) -> Dict:
        """Get database statistics like total opportunities, sources, etc."""
        cursor = self.conn.cursor()
        stats = {}
        
        # Total opportunities
        cursor.execute("SELECT COUNT(*) as count FROM opportunities")
        stats["total_opportunities"] = cursor.fetchone()["count"]
        
        # Opportunities by source
        cursor.execute("SELECT source, COUNT(*) as count FROM opportunities GROUP BY source")
        stats["by_source"] = {row["source"]: row["count"] for row in cursor.fetchall()}
        
        # Opportunities by status
        cursor.execute("SELECT status, COUNT(*) as count FROM opportunities GROUP BY status")
        stats["by_status"] = {row["status"]: row["count"] for row in cursor.fetchall()}
        
        # Opportunities by category
        cursor.execute("SELECT category, COUNT(*) as count FROM opportunities GROUP BY category")
        stats["by_category"] = {row["category"]: row["count"] for row in cursor.fetchall()}
        
        # Most common tags
        cursor.execute("""
        SELECT tag, COUNT(*) as count 
        FROM opportunity_tags 
        GROUP BY tag 
        ORDER BY count DESC 
        LIMIT 20
        """)
        stats["top_tags"] = {row["tag"]: row["count"] for row in cursor.fetchall()}
        
        # New opportunities in the last 24 hours
        cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute("SELECT COUNT(*) as count FROM opportunities WHERE last_updated >= ?", (cutoff_time,))
        stats["new_last_24h"] = cursor.fetchone()["count"]
        
        # Value statistics
        cursor.execute("""
        SELECT 
            MIN(value_amount) as min_value,
            MAX(value_amount) as max_value,
            AVG(value_amount) as avg_value,
            SUM(value_amount) as total_value
        FROM opportunities
        WHERE value_amount IS NOT NULL
        """)
        row = cursor.fetchone()
        stats["value_stats"] = {
            "min": row["min_value"],
            "max": row["max_value"],
            "avg": row["avg_value"],
            "total": row["total_value"]
        }
        
        return stats
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
        logger.info("Closed database connection")
