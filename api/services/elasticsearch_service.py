"""
Elasticsearch service for job storage and search
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from api.core.elasticsearch_config import get_elasticsearch_client
from api.core.config import settings

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Service for Elasticsearch operations"""
    
    def __init__(self):
        self.client = get_elasticsearch_client()
        self.index = settings.ELASTICSEARCH_INDEX
    
    def save_job(self, job: Dict) -> Dict[str, Any]:
        """
        Save a single job to Elasticsearch
        
        Args:
            job: Job data dictionary
            
        Returns:
            Result dictionary with success status
        """
        if not self.client:
            return {"success": False, "error": "Elasticsearch not connected"}
        
        try:
            # Add timestamp
            job['scraped_at'] = datetime.utcnow().isoformat()
            
            # Use job_id as document ID for deduplication
            doc_id = job.get('job_id', None)
            
            if doc_id:
                result = self.client.index(
                    index=self.index,
                    id=doc_id,
                    document=job
                )
            else:
                result = self.client.index(
                    index=self.index,
                    document=job
                )
            
            return {
                "success": True,
                "id": result['_id'],
                "result": result['result']
            }
            
        except Exception as e:
            logger.error(f"Error saving job to Elasticsearch: {e}")
            return {"success": False, "error": str(e)}
    
    def save_jobs_bulk(self, jobs: List[Dict]) -> Dict[str, Any]:
        """
        Save multiple jobs to Elasticsearch using bulk API
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            Result dictionary with success/failed counts
        """
        if not self.client:
            return {
                "success": 0,
                "failed": len(jobs),
                "error": "Elasticsearch not connected"
            }
        
        if not jobs:
            return {"success": 0, "failed": 0, "error": "No jobs to save"}
        
        try:
            from elasticsearch.helpers import bulk
            
            # Prepare bulk actions
            actions = []
            for job in jobs:
                # Add timestamp
                job['scraped_at'] = datetime.utcnow().isoformat()
                
                action = {
                    "_index": self.index,
                    "_source": job
                }
                
                # Use job_id as document ID if available
                if job.get('job_id'):
                    action['_id'] = job['job_id']
                
                actions.append(action)
            
            # Execute bulk insert
            success, failed = bulk(
                self.client,
                actions,
                stats_only=True,
                raise_on_error=False
            )
            
            logger.info(f"Elasticsearch bulk save: {success} succeeded, {failed} failed")
            
            return {
                "success": success,
                "failed": failed,
                "total": len(jobs)
            }
            
        except Exception as e:
            logger.error(f"Error in bulk save to Elasticsearch: {e}")
            return {
                "success": 0,
                "failed": len(jobs),
                "error": str(e)
            }
    
    def search_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        skills: Optional[List[str]] = None,
        employment_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Search jobs in Elasticsearch
        
        Args:
            query: Search query for title/description
            location: Filter by location
            company: Filter by company
            skills: Filter by skills
            employment_type: Filter by employment type
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Dictionary with hits and total count
        """
        if not self.client:
            return {
                "total": 0,
                "hits": [],
                "error": "Elasticsearch not connected"
            }
        
        try:
            # Build query
            must_clauses = []
            filter_clauses = []
            
            # Full-text search on title and description
            if query:
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "description"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                })
            
            # Location filter
            if location:
                filter_clauses.append({
                    "match": {
                        "location": {
                            "query": location,
                            "fuzziness": "AUTO"
                        }
                    }
                })
            
            # Company filter
            if company:
                filter_clauses.append({
                    "match": {
                        "company": company
                    }
                })
            
            # Skills filter
            if skills:
                filter_clauses.append({
                    "terms": {
                        "skills": skills
                    }
                })
            
            # Employment type filter
            if employment_type:
                filter_clauses.append({
                    "term": {
                        "employment_type": employment_type
                    }
                })
            
            # Build final query
            if must_clauses or filter_clauses:
                search_query = {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                        "filter": filter_clauses
                    }
                }
            else:
                search_query = {"match_all": {}}
            
            # Calculate pagination
            from_index = (page - 1) * page_size
            
            # Execute search
            result = self.client.search(
                index=self.index,
                query=search_query,
                from_=from_index,
                size=page_size,
                sort=[{"scraped_at": {"order": "desc"}}]
            )
            
            # Extract hits
            hits = [
                {
                    "_id": hit["_id"],
                    "_score": hit["_score"],
                    **hit["_source"]
                }
                for hit in result["hits"]["hits"]
            ]
            
            return {
                "total": result["hits"]["total"]["value"],
                "hits": hits,
                "page": page,
                "page_size": page_size,
                "pages": (result["hits"]["total"]["value"] + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"Error searching Elasticsearch: {e}")
            return {
                "total": 0,
                "hits": [],
                "error": str(e)
            }
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict]:
        """
        Get a specific job by ID
        
        Args:
            job_id: Job ID
            
        Returns:
            Job data or None
        """
        if not self.client:
            return None
        
        try:
            result = self.client.get(index=self.index, id=job_id)
            return {
                "_id": result["_id"],
                **result["_source"]
            }
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            return None
    
    def delete_job(self, job_id: str) -> Dict[str, Any]:
        """
        Delete a job by ID
        
        Args:
            job_id: Job ID
            
        Returns:
            Result dictionary
        """
        if not self.client:
            return {"success": False, "error": "Elasticsearch not connected"}
        
        try:
            result = self.client.delete(index=self.index, id=job_id)
            return {
                "success": True,
                "result": result["result"]
            }
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_aggregations(self) -> Dict[str, Any]:
        """
        Get aggregated statistics
        
        Returns:
            Dictionary with aggregations
        """
        if not self.client:
            return {"error": "Elasticsearch not connected"}
        
        try:
            result = self.client.search(
                index=self.index,
                size=0,
                aggs={
                    "top_companies": {
                        "terms": {
                            "field": "company.keyword",
                            "size": 10
                        }
                    },
                    "top_locations": {
                        "terms": {
                            "field": "location.keyword",
                            "size": 10
                        }
                    },
                    "top_skills": {
                        "terms": {
                            "field": "skills",
                            "size": 20
                        }
                    },
                    "employment_types": {
                        "terms": {
                            "field": "employment_type"
                        }
                    },
                    "by_country": {
                        "terms": {
                            "field": "country_code",
                            "size": 10
                        }
                    },
                    "by_role": {
                        "terms": {
                            "field": "job_role",
                            "size": 10
                        }
                    }
                }
            )
            
            # Extract aggregation results
            aggs = result.get("aggregations", {})
            
            return {
                "total_jobs": result["hits"]["total"]["value"],
                "top_companies": [
                    {"name": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in aggs.get("top_companies", {}).get("buckets", [])
                ],
                "top_locations": [
                    {"location": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in aggs.get("top_locations", {}).get("buckets", [])
                ],
                "top_skills": [
                    {"skill": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in aggs.get("top_skills", {}).get("buckets", [])
                ],
                "employment_types": [
                    {"type": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in aggs.get("employment_types", {}).get("buckets", [])
                ],
                "by_country": [
                    {"country": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in aggs.get("by_country", {}).get("buckets", [])
                ],
                "by_role": [
                    {"role": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in aggs.get("by_role", {}).get("buckets", [])
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting aggregations: {e}")
            return {"error": str(e)}
    
    def count_jobs(self) -> int:
        """
        Get total job count
        
        Returns:
            Total number of jobs in index
        """
        if not self.client:
            return 0
        
        try:
            result = self.client.count(index=self.index)
            return result["count"]
        except Exception as e:
            logger.error(f"Error counting jobs: {e}")
            return 0


# Singleton instance
elasticsearch_service = ElasticsearchService()
