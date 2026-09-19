"""Cohzen Manifest v0.1 Specification.

The Cohzen Manifest is the central machine-readable contract representing the
statically reconstructed architecture of an agentic application:
Normalized Graphs, Nodes, Edges, Models, Tools, and Compilation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceLocation(BaseModel):
    """Normalized source code location for AST entities."""
    file: str
    line_start: int
    line_end: int
    column_start: Optional[int] = None
    column_end: Optional[int] = None


class ResolutionDef(BaseModel):
    """Symbol resolution metadata."""
    status: str = Field(default="resolved", description="Resolution status: 'resolved', 'partially_resolved', or 'unresolved'")
    reason: Optional[str] = Field(default=None, description="Reason if not fully resolved: 'external_import', 'dynamic_expression', 'missing_symbol', etc.")
    package: Optional[str] = Field(default=None, description="External library or module name if imported from outside repository")


class NodeClassification(BaseModel):
    """Optional, non-authoritative heuristic classification for a graph node."""
    role: str = Field(description="Inferred classification: 'agent', 'tool_node', 'router', 'subgraph', 'logic'")
    confidence: str = Field(default="high", description="Confidence level: 'high', 'medium', 'low'")
    evidence: List[str] = Field(default_factory=list, description="Static cues observed: e.g. ['llm_invocation', 'tool_binding']")


class ModelDef(BaseModel):
    """Normalized specification of an LLM call site or model reference."""
    id: str = Field(description="Unique stable ID, e.g. 'model.openai.gpt-4o' or 'model.anthropic.claude-3-5-sonnet'")
    provider: str = Field(description="LLM provider: openai, anthropic, google, groq, grok, langchain, litellm")
    name: str = Field(description="Model identifier if known (e.g. 'gpt-4o') or caller signature")
    source: Optional[SourceLocation] = Field(default=None, description="Source code location of definition or invocation")


class ToolDef(BaseModel):
    """Normalized specification of an executable tool detected in the system."""
    id: str = Field(description="Unique stable ID, e.g. 'tool.search_web'")
    name: str = Field(description="Tool identifier or function name")
    source: Optional[SourceLocation] = Field(default=None, description="Source code location where tool is defined")
    docstring: Optional[str] = Field(default=None, description="Tool purpose or docstring")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Tool parameter schema if statically resolved")
    resolution: ResolutionDef = Field(default_factory=ResolutionDef, description="Tool symbol resolution status")


class CompilationDef(BaseModel):
    """Specification of graph compilation metadata."""
    compiled_var: str = Field(description="Variable assigned to compiled app (e.g. 'app')")
    checkpointer: Optional[str] = Field(default=None, description="State persistence checkpointer class or variable")
    interrupt_before: List[str] = Field(default_factory=list, description="Node IDs flagged for interrupt_before")
    interrupt_after: List[str] = Field(default_factory=list, description="Node IDs flagged for interrupt_after")
    store: Optional[str] = Field(default=None, description="Shared state store if configured")
    source: Optional[SourceLocation] = Field(default=None, description="Source code location where .compile() occurred")


class EdgeDef(BaseModel):
    """Specification of a topology connection between nodes in the graph."""
    source: str = Field(description="Source node identifier or START sentinel")
    target: str = Field(description="Target node identifier, END sentinel, or routing target")
    edge_type: str = Field(default="standard", description="Edge type: standard, conditional, entry_point, finish_point")
    condition_fn: Optional[str] = Field(default=None, description="Router function name for conditional edges")
    conditional_mapping: Optional[Dict[str, str]] = Field(default=None, description="Branch value to target mapping")
    location: Optional[SourceLocation] = Field(default=None, description="Source code location of edge declaration")


class NodeDef(BaseModel):
    """Factual specification of a discovered node in the agentic system.

    Static analysis establishes factually that a node is registered in a graph (kind='node').
    Subjective roles ('agent', 'router') are kept in the optional non-authoritative classification.
    """
    id: str = Field(description="Unique stable node ID in the graph, e.g. 'planner'")
    name: str = Field(description="Registered node name")
    kind: str = Field(default="node", description="Authoritative architectural primitive: 'node'")
    handler: str = Field(description="Callable function, runnable, or tool handler name")
    source: Optional[SourceLocation] = Field(default=None, description="Source location of node handler or registration")
    model_ids: List[str] = Field(default_factory=list, description="Referenced model IDs invoked within this node")
    tool_ids: List[str] = Field(default_factory=list, description="Referenced tool IDs bound or attached to this node")
    prompts: List[str] = Field(default_factory=list, description="Prompts or templates referenced statically")
    resolution: ResolutionDef = Field(default_factory=ResolutionDef, description="Handler symbol resolution status")
    classification: Optional[NodeClassification] = Field(default=None, description="Optional non-authoritative classification")


class GraphDef(BaseModel):
    """Specification of a discovered agentic graph with normalized node references."""
    id: str = Field(description="Unique stable graph ID, e.g. 'graph.workflow'")
    name: str = Field(description="Graph variable name (e.g. 'workflow', 'builder')")
    framework: str = Field(default="langgraph", description="Framework: langgraph")
    graph_class: str = Field(default="StateGraph", description="Graph class (e.g. StateGraph, MessageGraph)")
    state_schema: Optional[str] = Field(default=None, description="State schema class (e.g. AgentState, MessagesState)")
    source: Optional[SourceLocation] = Field(default=None, description="Source code location where graph is instantiated")
    node_ids: List[str] = Field(default_factory=list, description="IDs of registered nodes in this graph")
    edges: List[EdgeDef] = Field(default_factory=list, description="Edges and routing topology")
    compilation: Optional[CompilationDef] = Field(default=None, description="Compilation metadata if compiled")

    @property
    def is_compiled(self) -> bool:
        return self.compilation is not None


class ManifestMetadata(BaseModel):
    """Metadata about the repository scan that generated this manifest."""
    target: str = Field(description="Root path scanned")
    files_scanned: int = Field(default=0, description="Total files examined")
    files_skipped: int = Field(default=0, description="Files skipped during scan")
    parse_errors: int = Field(default=0, description="Files with parse errors")
    unresolved_symbols: int = Field(default=0, description="Symbols that could not be statically resolved")
    dynamic_constructions: int = Field(default=0, description="Dynamic graph/tool expressions encountered")
    external_imports: int = Field(default=0, description="Components imported from external libraries")
    external_packages: List[str] = Field(default_factory=list, description="External library package names detected")
    scan_duration_ms: float = Field(default=0.0, description="Scan duration in milliseconds")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of scan")
    warnings: List[str] = Field(default_factory=list, description="Explicit static analysis limitations or caveats")


class CohzenManifest(BaseModel):
    """The Cohzen System Manifest v0.1.

    The central machine-readable contract defining an agentic system's architecture.
    Normalized structure with top-level graphs, nodes, tools, and models.
    """
    version: str = Field(default="0.1.0", description="Cohzen Manifest schema version")
    metadata: ManifestMetadata = Field(description="Scan execution metadata")
    frameworks: List[str] = Field(default_factory=lambda: ["langgraph"], description="Detected frameworks")
    graphs: List[GraphDef] = Field(default_factory=list, description="Discovered agentic graphs")
    nodes: List[NodeDef] = Field(default_factory=list, description="Normalized registered nodes")
    tools: List[ToolDef] = Field(default_factory=list, description="Discovered tool definitions")
    models: List[ModelDef] = Field(default_factory=list, description="Discovered model definitions")

    @property
    def total_graphs(self) -> int:
        return len(self.graphs)

    @property
    def total_nodes(self) -> int:
        return len(self.nodes)

    @property
    def total_edges(self) -> int:
        return sum(len(g.edges) for g in self.graphs)

    @property
    def total_tools(self) -> int:
        return len(self.tools)

    @property
    def total_models(self) -> int:
        return len(self.models)
