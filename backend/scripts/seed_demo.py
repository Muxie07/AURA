import asyncio
import os
import sys
import uuid
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database.base import close_database, get_session_factory, initialize_database
from app.database.models import (
    AgentRun, AgentRunStatus, AgentTraceEvent, ApprovalRequest, ApprovalStatus,
    AuditEvent, AuditEventType, Conversation, ConversationStatus, Document,
    DocumentChunk, DocumentStatus, KnowledgeBase, Message, MessageRole,
    Organization, ToolCall, ToolCallStatus, ToolExecutionAudit, User, Customer, Product, Quotation
)

PASSWORD_HASH = '$2b$12$1YhZv42JKpAkpOxL2sl8sOz/pTDXgpnHRK/U8PPdlrUChzkTMvnWC' # demo1234

async def seed_data():
    print('Initializing database connection...')
    await initialize_database()
    factory = get_session_factory()
    
    async with factory() as session:
        # Clear existing demo data
        org_slugs = ['aura-demo-inc', 'global-enterprises-ltd', 'nova-systems']
        for slug in org_slugs:
            result = await session.execute(select(Organization).where(Organization.slug == slug))
            demo_org = result.scalar_one_or_none()
            if demo_org:
                await session.delete(demo_org)
        await session.commit()
        
        # 1. Organizations
        now = datetime.utcnow()
        org1 = Organization(name='AURA Demo Inc', slug='aura-demo-inc', settings={'tier': 'enterprise', 'features': ['hitl', 'rag']})
        org2 = Organization(name='Global Enterprises Ltd', slug='global-enterprises-ltd', settings={'tier': 'pro', 'features': ['hitl']})
        org3 = Organization(name='Nova Systems', slug='nova-systems', settings={'tier': 'enterprise', 'features': ['hitl', 'rag']})
        session.add_all([org1, org2, org3])
        await session.flush()
        
        # 2. Users
        users = []
        # Org 1 Users
        u1_admin = User(organization_id=org1.id, email='admin@aura-sre.com', full_name='Admin User', is_superuser=True, hashed_password=PASSWORD_HASH, metadata_={'role': 'Admin'})
        u1_manager = User(organization_id=org1.id, email='manager@aura-sre.com', full_name='Manager User', is_superuser=False, hashed_password=PASSWORD_HASH, metadata_={'role': 'Manager'})
        u1_demo = User(organization_id=org1.id, email='demo@aura-sre.com', full_name='Demo Operator', is_superuser=True, hashed_password=PASSWORD_HASH, metadata_={'role': 'Lead SRE'})
        u1_analyst = User(organization_id=org1.id, email='analyst@aura-sre.com', full_name='Analyst User', is_superuser=False, hashed_password=PASSWORD_HASH, metadata_={'role': 'Analyst'})
        
        # Org 2 & 3 Users
        u2_admin = User(organization_id=org2.id, email='admin@global-enterprises.com', full_name='Global Admin', is_superuser=True, hashed_password=PASSWORD_HASH, metadata_={'role': 'Admin'})
        u3_admin = User(organization_id=org3.id, email='admin@nova-systems.com', full_name='Nova Admin', is_superuser=True, hashed_password=PASSWORD_HASH, metadata_={'role': 'Admin'})
        
        session.add_all([u1_admin, u1_manager, u1_demo, u1_analyst, u2_admin, u3_admin])
        await session.flush()

        # Demo Entity Identifiers expected by heuristic
        org1_hex = str(org1.id).replace("-", "")[:8]
        org1_uuid_str = str(org1.id)[:8] # e.g. "a2f37be1"

        cust1 = Customer(id="cust-001", organization_id=org1.id, name="Acme Technologies", email="contact@acme.com")
        cust2 = Customer(id=f"CUST-001-{org1_uuid_str}", organization_id=org1.id, name="Acme Technologies (Fallback)", email="contact2@acme.com")
        cust3 = Customer(id="CUST-003", organization_id=org1.id, name="Nova Engineering", email="procurement@nova.net")
        
        # Products
        prod1 = Product(id=f"PROD-X-{org1_uuid_str}", organization_id=org1.id, name="Enterprise Database Server", sku="ENT-DB-001", availability="in_stock", base_price=5000.00)
        prod2 = Product(id="prod-x", organization_id=org1.id, name="Enterprise Database Server", sku="ENT-DB-002", availability="in_stock", base_price=5000.00)
        prod3 = Product(id="PROD-X", organization_id=org1.id, name="Enterprise Database Server", sku="ENT-DB-003", availability="in_stock", base_price=5000.00)
        prod4 = Product(id="PROD-AI", organization_id=org1.id, name="AI Analytics Platform", sku="AI-PLAT-100", availability="in_stock", base_price=3500.00)

        session.add_all([cust1, cust2, cust3, prod1, prod2, prod3, prod4])
        await session.flush()



        # 3. Knowledge Bases
        kbs = []
        kb_topics = [
            ("SRE Runbooks", "Standard operating procedures for infrastructure"),
            ("Company Policies", "HR and company-wide policies"),
            ("Product Documentation", "Technical product docs"),
            ("Customer Support Knowledge", "Support articles and FAQs"),
            ("Sales Playbooks", "Sales strategies and scripts"),
            ("Security Procedures", "Security incident response plans")
        ]
        
        for name, desc in kb_topics:
            kb = KnowledgeBase(organization_id=org1.id, name=name, description=desc)
            session.add(kb)
            kbs.append(kb)
        await session.flush()
        
        # 4. Documents & Chunks
        for i, kb in enumerate(kbs):
            doc = Document(
                knowledge_base_id=kb.id, organization_id=org1.id,
                filename=f'{kb.name.lower().replace(" ", "_")}_v1.md',
                content_type='text/markdown', file_size=2048 + (i * 100),
                status=DocumentStatus.READY, indexed_at=now - timedelta(days=2)
            )
            session.add(doc)
            await session.flush()
            
            chunk = DocumentChunk(
                document_id=doc.id, organization_id=org1.id,
                chunk_index=0, content=f'This is the core content for {kb.name}. Important policies and procedures are outlined here.',
                token_count=18, embedding=[0.01]*1536, embedding_model='text-embedding-3-small'
            )
            session.add(chunk)
            
        await session.flush()

        # 5. Conversations & Agent Runs (15+ across topics)
        conv_topics = [
            ("Investigating production API latency", u1_demo, org1),
            ("Customer churn analysis", u1_analyst, org1),
            ("Sales pipeline analysis", u1_manager, org1),
            ("Infrastructure cost optimization", u1_admin, org1),
            ("Failed deployment investigation", u1_demo, org1),
            ("Support ticket prioritization", u1_manager, org1),
            ("Revenue performance analysis", u1_analyst, org1),
            ("Database performance investigation", u1_demo, org1),
            ("Security incident investigation", u1_admin, org1),
            ("Marketing campaign analysis", u1_analyst, org1),
            ("Employee productivity insights", u1_manager, org1),
            ("Inventory forecasting", u1_analyst, org1),
            ("Customer complaint analysis", u1_manager, org1),
            ("Cloud resource optimization", u1_demo, org1),
            ("Monthly business intelligence report", u1_admin, org1),
            ("Global Network partition alert", u2_admin, org2),
            ("Nova Database Migration Planning", u3_admin, org3)
        ]

        runs = []
        app_reqs = []
        
        for idx, (title, user, org) in enumerate(conv_topics):
            status = ConversationStatus.COMPLETED
            if idx % 5 == 0:
                status = ConversationStatus.ACTIVE
            
            conv = Conversation(organization_id=org.id, user_id=user.id, title=title, status=status, created_at=now - timedelta(days=idx))
            session.add(conv)
            await session.flush()
            
            msg1 = Message(conversation_id=conv.id, role=MessageRole.USER, content=f'Please help with: {title}')
            session.add(msg1)
            await session.flush()

            run_status = AgentRunStatus.COMPLETED
            if idx == 0: run_status = AgentRunStatus.RUNNING
            elif idx == 1: run_status = AgentRunStatus.AWAITING_APPROVAL
            elif idx == 2: run_status = AgentRunStatus.FAILED
            
            error_msg = 'API timeout' if run_status == AgentRunStatus.FAILED else None
            
            run = AgentRun(
                conversation_id=conv.id, user_id=user.id, status=run_status,
                user_request=f'Please help with: {title}',
                started_at=now - timedelta(days=idx),
                completed_at=(now - timedelta(days=idx) + timedelta(minutes=5)) if run_status in [AgentRunStatus.COMPLETED, AgentRunStatus.FAILED] else None,
                iteration_count=3, tool_call_count=2,
                plan={'steps': ['Analyze request', 'Retrieve knowledge', 'Execute tool', 'Verify']},
                final_response=f'Completed task: {title}' if run_status == AgentRunStatus.COMPLETED else None,
                error_message=error_msg,
                total_tokens_input=random.randint(500, 2000),
                total_tokens_output=random.randint(200, 800),
                latency_ms=random.randint(2000, 15000)
            )
            session.add(run)
            await session.flush()
            runs.append(run)

            # Trace Events
            trace1 = AgentTraceEvent(organization_id=org.id, run_id=run.id, sequence=1, event_type='plan_created', component='planner', timestamp=run.started_at + timedelta(seconds=2), duration_ms=1200, metadata_={'plan': run.plan})
            trace2 = AgentTraceEvent(organization_id=org.id, run_id=run.id, sequence=2, event_type='knowledge_retrieval', component='rag', timestamp=run.started_at + timedelta(seconds=4), duration_ms=800, metadata_={'query': title})
            session.add_all([trace1, trace2])

            # Tools & Approvals
            if run_status == AgentRunStatus.COMPLETED:
                tc = ToolCall(agent_run_id=run.id, tool_name='customer.search', status=ToolCallStatus.SUCCESS, input_args={'query': 'Acme'}, output={'result': 'Found Acme Corp'}, started_at=run.started_at + timedelta(seconds=10), completed_at=run.started_at + timedelta(seconds=11))
                session.add(tc)
                
                # Create an approved request for every 4th run
                if idx % 4 == 0:
                    tc2 = ToolCall(agent_run_id=run.id, tool_name='restart_service', status=ToolCallStatus.SUCCESS, input_args={'service': 'nginx'}, output={'result': 'Service restarted'}, started_at=run.started_at + timedelta(minutes=1), completed_at=run.started_at + timedelta(minutes=1, seconds=5))
                    session.add(tc2)
                    await session.flush()
                    app_req = ApprovalRequest(agent_run_id=run.id, organization_id=org.id, tool_name='restart_service', action_summary='Restart nginx', action_details={'service': 'nginx'}, status=ApprovalStatus.APPROVED, actioned_by_id=user.id, actioned_at=run.started_at + timedelta(minutes=1, seconds=2))
                    session.add(app_req)
                    await session.flush()
                    tc2.approval_id = app_req.id
                    
            elif run_status == AgentRunStatus.AWAITING_APPROVAL:
                tc = ToolCall(agent_run_id=run.id, tool_name='kill_process', status=ToolCallStatus.AWAITING_APPROVAL, input_args={'pid': 4519})
                session.add(tc)
                await session.flush()
                app_req = ApprovalRequest(agent_run_id=run.id, organization_id=org.id, tool_name='kill_process', action_summary='Kill process 4519', action_details={'pid': 4519}, status=ApprovalStatus.PENDING)
                session.add(app_req)
                await session.flush()
                tc.approval_id = app_req.id
                
            elif run_status == AgentRunStatus.FAILED:
                # Add a rejected request scenario here just to have one in the mix
                if idx % 2 == 0:
                    tc = ToolCall(agent_run_id=run.id, tool_name='order.create', status=ToolCallStatus.FAILED, input_args={'item': 'Server'}, error_message='Approval denied')
                    session.add(tc)
                    await session.flush()
                    app_req = ApprovalRequest(agent_run_id=run.id, organization_id=org.id, tool_name='order.create', action_summary='Create order', action_details={'item': 'Server'}, status=ApprovalStatus.DENIED, actioned_by_id=user.id, actioned_at=run.started_at + timedelta(minutes=1))
                    session.add(app_req)
                    await session.flush()
                    tc.approval_id = app_req.id

        await session.commit()
        print('Massive enterprise demo data seeded successfully!')

async def main():
    try:
        await seed_data()
    finally:
        await close_database()

if __name__ == "__main__":
    asyncio.run(main())
