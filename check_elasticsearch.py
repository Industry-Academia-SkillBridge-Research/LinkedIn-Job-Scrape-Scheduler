"""
Quick Elasticsearch Connection Check
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("\n" + "="*60)
print("🔍 ELASTICSEARCH CONNECTION CHECK")
print("="*60 + "\n")

try:
    print("1️⃣  Importing Elasticsearch client...")
    from api.core.elasticsearch_config import es_client
    from api.core.config import settings
    print("   ✅ Import successful\n")
    
    print("2️⃣  Checking connection...")
    print(f"   Host: {settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}")
    print(f"   Enabled: {settings.ELASTICSEARCH_ENABLED}")
    
    if es_client.is_connected:
        print("   ✅ Elasticsearch is CONNECTED\n")
        
        print("3️⃣  Getting cluster info...")
        info = es_client.client.info()
        print(f"   Cluster Name: {info['cluster_name']}")
        print(f"   Cluster UUID: {info['cluster_uuid']}")
        print(f"   Version: {info['version']['number']}")
        print(f"   Build: {info['version']['build_flavor']}\n")
        
        print("4️⃣  Checking index...")
        index_name = settings.ELASTICSEARCH_INDEX
        index_exists = es_client.client.indices.exists(index=index_name)
        
        if index_exists:
            print(f"   ✅ Index '{index_name}' EXISTS")
            
            # Get index stats
            stats = es_client.client.count(index=index_name)
            print(f"   Document Count: {stats['count']}\n")
        else:
            print(f"   ⚠️  Index '{index_name}' does NOT exist")
            print(f"   (Will be auto-created on first job save)\n")
        
        print("5️⃣  Testing search capability...")
        from api.services.elasticsearch_service import elasticsearch_service
        print(f"   Service Index: {elasticsearch_service.index}")
        print(f"   Client Status: {'Active' if elasticsearch_service.client else 'Not initialized'}\n")
        
        print("="*60)
        print("✅ ELASTICSEARCH IS READY TO USE!")
        print("="*60)
        print("\n💡 Next Steps:")
        print("   - Start API: python api/main.py")
        print("   - Run scheduler: curl -X POST http://localhost:8000/api/v1/scheduler/run-now")
        print("   - Search jobs: curl http://localhost:8000/api/v1/search")
        print("   - View analytics: curl http://localhost:8000/api/v1/analytics\n")
        
    else:
        print("   ❌ Elasticsearch is NOT CONNECTED\n")
        print("🔧 Troubleshooting:")
        print("   1. Check if Elasticsearch is running:")
        print("      curl http://localhost:9200")
        print("   2. Start Elasticsearch with Docker:")
        print("      docker-compose up -d elasticsearch")
        print("   3. Check .env configuration:")
        print("      ELASTICSEARCH_ENABLED=True")
        print("      ELASTICSEARCH_HOST=localhost")
        print("      ELASTICSEARCH_PORT=9200\n")
        
except ImportError as e:
    print(f"   ❌ Import Error: {e}\n")
    print("🔧 Fix:")
    print("   pip install elasticsearch\n")
    
except Exception as e:
    print(f"   ❌ Error: {e}\n")
    print("🔧 Troubleshooting:")
    print("   - Check if Elasticsearch is running: curl http://localhost:9200")
    print("   - Verify .env settings")
    print("   - Check docker-compose logs: docker-compose logs elasticsearch\n")
