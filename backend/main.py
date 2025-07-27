# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import uuid
from datetime import datetime
import re

app = FastAPI(title="Multi-Agent Coordination System with API Discovery")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatMessage(BaseModel):
    message: str

class TaskResponse(BaseModel):
    task_id: str
    status: str
    subtasks: List[Dict[str, Any]]
    results: Dict[str, Any]
    chat_response: str
    new_integrations: List[Dict[str, Any]] = []

class Integration(BaseModel):
    name: str
    base_url: str
    auth_type: str
    endpoints: Dict[str, str]
    capabilities: List[str]
    status: str
    created_at: str

# API Discovery Database - Known SaaS APIs
KNOWN_APIS = {
    "trello": {
        "name": "Trello",
        "base_url": "https://api.trello.com/1",
        "auth_type": "API_KEY",
        "endpoints": {
            "create_board": "/boards",
            "create_card": "/cards",
            "get_boards": "/members/me/boards",
            "add_member": "/boards/{id}/members"
        },
        "capabilities": ["create_board", "create_card", "manage_members", "get_boards"],
        "keywords": ["trello", "board", "card", "kanban"]
    },
    "clickup": {
        "name": "ClickUp",
        "base_url": "https://api.clickup.com/api/v2",
        "auth_type": "API_KEY",
        "endpoints": {
            "create_task": "/list/{list_id}/task",
            "get_teams": "/team",
            "create_list": "/folder/{folder_id}/list",
            "get_tasks": "/list/{list_id}/task"
        },
        "capabilities": ["create_task", "manage_lists", "get_teams", "task_management"],
        "keywords": ["clickup", "task", "project", "workspace"]
    },
    "slack": {
        "name": "Slack",
        "base_url": "https://slack.com/api",
        "auth_type": "OAUTH2",
        "endpoints": {
            "send_message": "/chat.postMessage",
            "create_channel": "/conversations.create",
            "get_channels": "/conversations.list",
            "invite_user": "/conversations.invite"
        },
        "capabilities": ["send_message", "create_channel", "manage_users", "get_channels"],
        "keywords": ["slack", "message", "channel", "chat", "team"]
    },
    "asana": {
        "name": "Asana",
        "base_url": "https://app.asana.com/api/1.0",
        "auth_type": "API_KEY",
        "endpoints": {
            "create_task": "/tasks",
            "create_project": "/projects",
            "get_projects": "/projects",
            "add_task_to_project": "/projects/{project_gid}/addTask"
        },
        "capabilities": ["create_task", "create_project", "manage_projects", "task_assignment"],
        "keywords": ["asana", "task", "project", "assignment"]
    },
    "airtable": {
        "name": "Airtable",
        "base_url": "https://api.airtable.com/v0",
        "auth_type": "API_KEY",
        "endpoints": {
            "create_record": "/{base_id}/{table_name}",
            "get_records": "/{base_id}/{table_name}",
            "update_record": "/{base_id}/{table_name}/{record_id}"
        },
        "capabilities": ["create_record", "get_records", "update_record", "manage_tables"],
        "keywords": ["airtable", "database", "record", "table", "base"]
    }
}

# Integration Manager
class IntegrationManager:
    def __init__(self):
        self.available_integrations = {
            "hubspot": Integration(
                name="HubSpot",
                base_url="https://api.hubapi.com",
                auth_type="API_KEY",
                endpoints={"get_contacts": "/crm/v3/objects/contacts", "create_contact": "/crm/v3/objects/contacts"},
                capabilities=["get_contacts", "create_contact", "manage_deals"],
                status="active",
                created_at="2025-01-01T00:00:00Z"
            ),
            "notion": Integration(
                name="Notion",
                base_url="https://api.notion.com/v1",
                auth_type="OAUTH2",
                endpoints={"search": "/search", "create_page": "/pages", "get_database": "/databases/{id}/query"},
                capabilities=["search", "create_page", "manage_databases", "get_notes"],
                status="active",
                created_at="2025-01-01T00:00:00Z"
            ),
            "gmail": Integration(
                name="Gmail",
                base_url="https://gmail.googleapis.com/gmail/v1",
                auth_type="OAUTH2",
                endpoints={"send": "/users/me/messages/send", "get": "/users/me/messages"},
                capabilities=["send_email", "read_email", "manage_labels"],
                status="active",
                created_at="2025-01-01T00:00:00Z"
            )
        }
    
    def discover_integration(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for relevant API based on query keywords"""
        query_lower = query.lower()
        
        for api_key, api_info in KNOWN_APIS.items():
            if api_key in self.available_integrations:
                continue
                
            # Check if any keywords match
            if any(keyword in query_lower for keyword in api_info["keywords"]):
                return api_info
        
        return None
    
    def add_integration(self, api_info: Dict[str, Any]) -> Integration:
        """Add new integration to available list"""
        integration = Integration(
            name=api_info["name"],
            base_url=api_info["base_url"],
            auth_type=api_info["auth_type"],
            endpoints=api_info["endpoints"],
            capabilities=api_info["capabilities"],
            status="stub",  # Mark as stub until real credentials provided
            created_at=datetime.now().isoformat()
        )
        
        api_key = api_info["name"].lower().replace(" ", "")
        self.available_integrations[api_key] = integration
        return integration
    
    def get_all_integrations(self) -> Dict[str, Integration]:
        """Return all available integrations"""
        return self.available_integrations

# Enhanced LLM Parser with API Discovery
class LLMParser:
    def __init__(self, integration_manager: IntegrationManager):
        self.integration_manager = integration_manager
    
    def parse_instruction(self, instruction: str) -> Dict[str, Any]:
        """Parse natural language into structured subtasks with API discovery"""
        instruction_lower = instruction.lower()
        
        subtasks = []
        new_integrations = []
        
        # Check for existing integrations first
        available_agents = list(self.integration_manager.available_integrations.keys())
        
        # HubSpot tasks
        if any(keyword in instruction_lower for keyword in ["hubspot", "lead", "contact", "crm"]):
            subtasks.append({
                "id": str(uuid.uuid4()),
                "agent": "hubspot",
                "action": "get_leads" if "get" in instruction_lower or "pull" in instruction_lower else "create_contact",
                "parameters": {"timeframe": "yesterday" if "yesterday" in instruction_lower else "today"},
                "dependencies": []
            })
        
        # Notion tasks
        if any(keyword in instruction_lower for keyword in ["notion", "notes", "meeting", "document"]):
            subtasks.append({
                "id": str(uuid.uuid4()),
                "agent": "notion",
                "action": "get_meeting_notes" if "notes" in instruction_lower else "create_page",
                "parameters": {"date": "yesterday" if "yesterday" in instruction_lower else "today"},
                "dependencies": []
            })
        
        # Gmail tasks
        if any(keyword in instruction_lower for keyword in ["email", "gmail", "send", "mail"]):
            deps = []
            if any("hubspot" in task.get("agent", "") for task in subtasks):
                deps.append("hubspot")
            if any("notion" in task.get("agent", "") for task in subtasks):
                deps.append("notion")
            
            subtasks.append({
                "id": str(uuid.uuid4()),
                "agent": "gmail",
                "action": "send_email",
                "parameters": {"type": "follow_up"},
                "dependencies": deps
            })
        
        # API Discovery - Check for unknown services
        discovered_api = self.integration_manager.discover_integration(instruction)
        if discovered_api:
            # Add new integration
            integration = self.integration_manager.add_integration(discovered_api)
            new_integrations.append({
                "name": integration.name,
                "status": "discovered",
                "capabilities": integration.capabilities
            })
            
            # Add task for new integration
            agent_key = discovered_api["name"].lower().replace(" ", "")
            action = self._determine_action_from_instruction(instruction, discovered_api["capabilities"])
            
            subtasks.append({
                "id": str(uuid.uuid4()),
                "agent": agent_key,
                "action": action,
                "parameters": self._extract_parameters(instruction),
                "dependencies": [],
                "is_new_integration": True
            })
        
        return {
            "original_instruction": instruction,
            "subtasks": subtasks,
            "execution_plan": "sequential" if len(subtasks) > 1 else "single",
            "new_integrations": new_integrations
        }
    
    def _determine_action_from_instruction(self, instruction: str, capabilities: List[str]) -> str:
        """Determine the most appropriate action based on instruction and capabilities"""
        instruction_lower = instruction.lower()
        
        if "create" in instruction_lower:
            create_actions = [cap for cap in capabilities if "create" in cap]
            return create_actions[0] if create_actions else capabilities[0]
        elif "get" in instruction_lower or "fetch" in instruction_lower:
            get_actions = [cap for cap in capabilities if "get" in cap]
            return get_actions[0] if get_actions else capabilities[0]
        else:
            return capabilities[0] if capabilities else "default_action"
    
    def _extract_parameters(self, instruction: str) -> Dict[str, Any]:
        """Extract parameters from instruction"""
        params = {}
        
        # Extract common parameters
        if "team" in instruction.lower():
            params["include_team"] = True
        if "yesterday" in instruction.lower():
            params["timeframe"] = "yesterday"
        if "urgent" in instruction.lower():
            params["priority"] = "high"
            
        return params

# Shared Task Memory
class TaskMemory:
    def __init__(self):
        self.data = {}
    
    def store(self, key: str, value: Any):
        self.data[key] = value
    
    def retrieve(self, key: str) -> Any:
        return self.data.get(key)
    
    def get_all(self) -> Dict[str, Any]:
        return self.data.copy()

# Base Agent Class
class BaseAgent:
    def __init__(self, name: str, memory: TaskMemory, integration: Integration):
        self.name = name
        self.memory = memory
        self.integration = integration
    
    def get_capabilities(self) -> List[str]:
        return self.integration.capabilities
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action - to be overridden by specific agents"""
        return {"status": "error", "message": f"Action {action} not implemented"}

# Existing Agents (Enhanced)
class HubSpotAgent(BaseAgent):
    async def get_leads(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(1)
        
        mock_leads = [
            {"id": "lead_001", "name": "John Smith", "email": "john.smith@techcorp.com", "company": "TechCorp Inc"},
            {"id": "lead_002", "name": "Sarah Johnson", "email": "sarah.j@innovate.io", "company": "Innovate Solutions"}
        ]
        
        self.memory.store("leads", mock_leads)
        return {"status": "success", "data": mock_leads, "message": f"Retrieved {len(mock_leads)} leads from HubSpot"}
    
    async def create_contact(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(1)
        
        contact = {"id": "contact_new", "name": "New Contact", "email": "new@example.com"}
        return {"status": "success", "data": contact, "message": "Created new contact in HubSpot"}

class NotionAgent(BaseAgent):
    async def get_meeting_notes(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(1.5)
        
        mock_notes = {
            "meeting_id": "zoom_meeting_001",
            "title": "Sales Discovery Call - July 25, 2025",
            "key_points": ["Budget approved for Q3", "Technical demo needed"],
            "action_items": ["Send pricing", "Schedule demo"]
        }
        
        self.memory.store("meeting_notes", mock_notes)
        return {"status": "success", "data": mock_notes, "message": "Retrieved meeting notes from Notion"}
    
    async def create_page(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(1)
        
        page = {"id": "page_new", "title": "New Page", "url": "https://notion.so/new-page"}
        return {"status": "success", "data": page, "message": "Created new page in Notion"}

class GmailAgent(BaseAgent):
    async def send_email(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(2)
        
        leads = self.memory.retrieve("leads") or []
        emails_sent = []
        
        for lead in leads:
            emails_sent.append({
                "to": lead["email"],
                "subject": "Follow-up from our call",
                "status": "sent"
            })
        
        self.memory.store("emails_sent", emails_sent)
        return {"status": "success", "data": emails_sent, "message": f"Sent {len(emails_sent)} emails via Gmail"}

# Dynamic Agent Factory
class DynamicAgent(BaseAgent):
    """Generic agent for newly discovered APIs"""
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action for dynamic integration"""
        await asyncio.sleep(1.5)  # Simulate API call
        
        # Mock responses based on integration type
        if self.integration.name == "Trello":
            return await self._handle_trello_action(action, parameters)
        elif self.integration.name == "ClickUp":
            return await self._handle_clickup_action(action, parameters)
        elif self.integration.name == "Slack":
            return await self._handle_slack_action(action, parameters)
        else:
            return await self._handle_generic_action(action, parameters)
    
    async def _handle_trello_action(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if action == "create_board":
            board = {
                "id": "board_001",
                "name": "New Project Board",
                "url": "https://trello.com/b/board_001"
            }
            self.memory.store("trello_board", board)
            return {"status": "success", "data": board, "message": "Created new Trello board"}
        return {"status": "success", "message": f"Executed {action} on Trello (mock)"}
    
    async def _handle_clickup_action(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if action == "create_task":
            task = {"id": "task_001", "name": "New Task", "status": "open"}
            return {"status": "success", "data": task, "message": "Created new ClickUp task"}
        return {"status": "success", "message": f"Executed {action} on ClickUp (mock)"}
    
    async def _handle_slack_action(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if action == "send_message":
            message = {"channel": "#general", "text": "Hello team!", "timestamp": datetime.now().isoformat()}
            return {"status": "success", "data": message, "message": "Sent Slack message"}
        return {"status": "success", "message": f"Executed {action} on Slack (mock)"}
    
    async def _handle_generic_action(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "success",
            "message": f"Executed {action} on {self.integration.name} (mock response)",
            "data": {"action": action, "parameters": parameters}
        }

# Enhanced Agent Manager
class AgentManager:
    def __init__(self, integration_manager: IntegrationManager):
        self.memory = TaskMemory()
        self.integration_manager = integration_manager
        self.agents = {}
        self._initialize_default_agents()
    
    def _initialize_default_agents(self):
        """Initialize default agents"""
        integrations = self.integration_manager.get_all_integrations()
        
        self.agents["hubspot"] = HubSpotAgent("hubspot", self.memory, integrations["hubspot"])
        self.agents["notion"] = NotionAgent("notion", self.memory, integrations["notion"])
        self.agents["gmail"] = GmailAgent("gmail", self.memory, integrations["gmail"])
    
    def get_or_create_agent(self, agent_name: str) -> BaseAgent:
        """Get existing agent or create dynamic agent for new integrations"""
        if agent_name in self.agents:
            return self.agents[agent_name]
        
        # Check if integration exists
        integrations = self.integration_manager.get_all_integrations()
        if agent_name in integrations:
            # Create dynamic agent
            agent = DynamicAgent(agent_name, self.memory, integrations[agent_name])
            self.agents[agent_name] = agent
            return agent
        
        raise ValueError(f"Agent {agent_name} not found and no integration available")
    
    async def execute_task(self, agent_name: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task with the specified agent"""
        try:
            agent = self.get_or_create_agent(agent_name)
            
            # Use specific method if available, otherwise use generic execute
            if hasattr(agent, action):
                result = await getattr(agent, action)(parameters)
            else:
                result = await agent.execute(action, parameters)
            
            return result
        except Exception as e:
            return {"status": "error", "message": f"Error executing {action} on {agent_name}: {str(e)}"}

# Enhanced Orchestrator
class Orchestrator:
    def __init__(self):
        self.integration_manager = IntegrationManager()
        self.parser = LLMParser(self.integration_manager)
        self.agent_manager = AgentManager(self.integration_manager)
    
    async def execute_instruction(self, instruction: str) -> TaskResponse:
        """Main orchestration logic with API discovery"""
        task_id = str(uuid.uuid4())
        
        # Parse instruction (includes API discovery)
        parsed = self.parser.parse_instruction(instruction)
        subtasks = parsed["subtasks"]
        new_integrations = parsed.get("new_integrations", [])
        
        # Execute subtasks with dependency handling
        results = {}
        execution_log = []
        
        for subtask in subtasks:
            # Check dependencies
            if subtask["dependencies"]:
                for dep in subtask["dependencies"]:
                    if dep not in [completed_task["agent"] for completed_task in execution_log]:
                        dep_task = next((t for t in subtasks if t["agent"] == dep), None)
                        if dep_task and dep_task["id"] not in [t["id"] for t in execution_log]:
                            dep_result = await self.agent_manager.execute_task(
                                dep_task["agent"], dep_task["action"], dep_task["parameters"]
                            )
                            execution_log.append({**dep_task, "result": dep_result})
                            results[dep_task["agent"]] = dep_result
            
            # Execute current subtask
            if subtask["id"] not in [t["id"] for t in execution_log]:
                result = await self.agent_manager.execute_task(
                    subtask["agent"], subtask["action"], subtask["parameters"]
                )
                execution_log.append({**subtask, "result": result})
                results[subtask["agent"]] = result
        
        # Generate chat response
        chat_response = self._generate_chat_response(results, new_integrations, parsed["original_instruction"])
        
        return TaskResponse(
            task_id=task_id,
            status="completed",
            subtasks=execution_log,
            results=results,
            chat_response=chat_response,
            new_integrations=new_integrations
        )
    
    def _generate_chat_response(self, results: Dict[str, Any], new_integrations: List[Dict], instruction: str) -> str:
        """Generate human-readable response including new integrations"""
        response_parts = []
        
        # Mention new integrations first
        if new_integrations:
            for integration in new_integrations:
                response_parts.append(f"🔌 **{integration['name']} API discovered and integrated!**")
        
        response_parts.append("✅ Task completed successfully!\n")
        
        for agent, result in results.items():
            if result["status"] == "success":
                response_parts.append(f"• {agent.title()}: {result['message']}")
            else:
                response_parts.append(f"• {agent.title()}: ❌ {result['message']}")
        
        return "\n".join(response_parts)

# Global orchestrator instance
orchestrator = Orchestrator()

# API Endpoints
@app.post("/api/chat", response_model=TaskResponse)
async def process_chat_message(message: ChatMessage):
    """Process chat message and execute multi-agent tasks with API discovery"""
    try:
        result = await orchestrator.execute_instruction(message.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/integrations")
async def get_integrations():
    """Get all available integrations"""
    integrations = orchestrator.integration_manager.get_all_integrations()
    return {
        "integrations": {
            name: {
                "name": integration.name,
                "capabilities": integration.capabilities,
                "status": integration.status,
                "auth_type": integration.auth_type,
                "created_at": integration.created_at
            }
            for name, integration in integrations.items()
        },
        "total": len(integrations)
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
