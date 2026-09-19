"""Core Pydantic models for cz AI/agentic architecture scanner."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, computed_field


class CompileInfo(BaseModel):
    """Information about where and how an agentic workflow/graph is compiled."""
    compiled_var: str = Field(description="Variable assigned to the compiled graph/app (e.g. 'app')")
    file_path: str = Field(description="Path to the file where .compile() is called")
    line_number: int = Field(description="Line number of .compile() call")
    checkpointer: Optional[str] = Field(default=None, description="Checkpointer argument if provided")
    interrupt_before: List[str] = Field(default_factory=list, description="Nodes flagged for interrupt_before")
    interrupt_after: List[str] = Field(default_factory=list, description="Nodes flagged for interrupt_after")
    store: Optional[str] = Field(default=None, description="Store argument if provided")


class PromptDef(BaseModel):
    """Information about a prompt definition."""
    var_name: str = Field(description="Variable name assigned to the prompt")
    template_type: str = Field(description="Type: ChatPromptTemplate, PromptTemplate, SystemMessage, etc.")
    snippet: Optional[str] = Field(default=None, description="Prompt text preview or template structure")
    file_path: str = Field(description="File where prompt is defined")
    line_number: int = Field(description="Line number where prompt is defined")


class ToolsBoundInfo(BaseModel):
    """Information about tools bound to a model (e.g. bind_tools or tools=[...])."""
    model_var: str = Field(description="Variable name of the model being bound")
    tools: List[str] = Field(default_factory=list, description="List of tools bound to the model")
    provider: str = Field(default="unknown", description="Provider/framework: langchain, openai, groq, etc.")
    file_path: str = Field(description="File where tools binding occurred")
    line_number: int = Field(description="Line number where tools binding occurred")


class ToolNodeDef(BaseModel):
    """Information about a ToolNode instance."""
    var_name: str = Field(description="Variable or node name for the ToolNode")
    tools: List[str] = Field(default_factory=list, description="List of tool references assigned")
    file_path: str = Field(description="File where ToolNode is defined")
    line_number: int = Field(description="Line number where ToolNode is defined")


class LLMCallSite(BaseModel):
    """Information about where an LLM is called inside an agent or script."""
    provider: str = Field(default="unknown", description="Provider: openai, anthropic, google, groq, grok, langchain, litellm")
    caller_var: str = Field(description="Variable name of the model, chain, or client invoked")
    method: str = Field(description="Method invoked (e.g. 'invoke', 'ainvoke', 'stream', 'chat.completions.create')")
    model_name: Optional[str] = Field(default=None, description="Model identifier if specified (e.g. 'gpt-4o', 'claude-3-5-sonnet')")
    input_arg: Optional[str] = Field(default=None, description="Argument or state passed into the call")
    tools_bound: List[str] = Field(default_factory=list, description="Tools passed in call parameters (e.g. tools=[...])")
    file_path: str = Field(description="File where LLM call occurs")
    line_number: int = Field(description="Line number of the LLM call")


class ToolDef(BaseModel):
    """Information about a tool function definition."""
    name: str = Field(description="Tool function name")
    file_path: str = Field(description="File path where tool is defined")
    line_start: int = Field(description="Starting line number of function")
    line_end: int = Field(description="Ending line number of function")
    docstring: Optional[str] = Field(default=None, description="Tool docstring description")
    has_tool_decorator: bool = Field(default=True, description="Whether decorated with @tool")
    is_instrumented: bool = Field(default=False, description="Whether tool has observability decorator/tracing")
    telemetry_decorators: List[str] = Field(default_factory=list, description="Tracing decorators detected")


class NodeDef(BaseModel):
    """Information about a node/function definition in an agentic system."""
    name: str = Field(description="Node handler/function name")
    file_path: str = Field(description="File path where node function is defined")
    line_start: int = Field(description="Starting line number of function")
    line_end: int = Field(description="Ending line number of function")
    is_async: bool = Field(default=False, description="Whether node function is async")
    docstring: Optional[str] = Field(default=None, description="Function docstring")
    role: str = Field(default="node", description="Derived role: agent, tool_node, router, subgraph, logic")
    llm_calls: List[LLMCallSite] = Field(default_factory=list, description="LLM invocations inside this node")
    prompts_used: List[str] = Field(default_factory=list, description="Prompt templates referenced or piped")
    tools_bound: List[str] = Field(default_factory=list, description="Bound tools referenced by this node")
    is_instrumented: bool = Field(default=False, description="Whether node function has observability decorator")
    telemetry_decorators: List[str] = Field(default_factory=list, description="Tracing decorators (e.g., @traceable, @observe)")


# Backward-compatible alias
AgentDef = NodeDef


class NodeInfo(BaseModel):
    """Information about an agent/node registered in an agentic graph."""
    name: str = Field(description="Identifier of the node/agent in the graph")
    handler: str = Field(description="Target function, runnable, or tool handler")
    file_path: str = Field(description="File where node is added")
    line_number: int = Field(description="Line number where node is added")
    is_subgraph: bool = Field(default=False, description="Whether this node references another compiled subgraph")
    agent_def: Optional[AgentDef] = Field(default=None, description="Resolved agent function definition if found")
    tool_node_def: Optional[ToolNodeDef] = Field(default=None, description="Resolved ToolNode definition if this node is a ToolNode")


class EdgeInfo(BaseModel):
    """Information about edges connecting nodes in the graph."""
    source: str = Field(description="Source node or START sentinel")
    target: str = Field(description="Target node, END sentinel, or condition summary")
    edge_type: str = Field(default="direct", description="Type: direct, conditional, entry_point, finish_point")
    condition_fn: Optional[str] = Field(default=None, description="Router/condition function for conditional edges")
    conditional_mapping: Dict[str, str] = Field(default_factory=dict, description="Dictionary mapping of return values to next nodes")
    file_path: str = Field(description="File where edge is defined")
    line_number: int = Field(description="Line number where edge is defined")


class GraphInfo(BaseModel):
    """Information about a detected agentic graph instance (e.g., LangGraph)."""
    framework: str = Field(default="langgraph", description="Agentic framework: langgraph, crewai, etc.")
    graph_var: str = Field(description="Variable name of the StateGraph/Graph builder")
    graph_class: str = Field(default="StateGraph", description="Graph class type (e.g., StateGraph, MessageGraph)")
    state_schema: Optional[str] = Field(default=None, description="State schema class (e.g., AgentState, MessagesState)")
    file_path: str = Field(description="Path to the file defining the graph")
    line_number: int = Field(description="Line number where graph is initialized")
    is_compiled: bool = Field(default=False, description="Whether .compile() was called on this graph")
    compile_info: Optional[CompileInfo] = Field(default=None, description="Compilation metadata if compiled")
    nodes: List[NodeInfo] = Field(default_factory=list, description="List of nodes/agents added to this graph")
    edges: List[EdgeInfo] = Field(default_factory=list, description="List of edges and routes in this graph")

    @property
    def agent_names(self) -> List[str]:
        return [node.name for node in self.nodes]


class ObservabilityPackage(BaseModel):
    """Detected observability or telemetry package."""
    name: str = Field(description="Package name (e.g. 'langsmith', 'langfuse')")
    provider_id: str = Field(description="Provider identifier (e.g. 'langsmith', 'langfuse')")
    category: str = Field(description="Category: Tracing, Metrics, Evaluation, APM")
    source_file: str = Field(description="File where detected (e.g. 'pyproject.toml', 'requirements.txt')")
    version_spec: Optional[str] = Field(default=None, description="Version constraint or specifier if declared")


class ObservabilityAudit(BaseModel):
    """Repository-wide observability and instrumentation audit."""
    packages: List[ObservabilityPackage] = Field(default_factory=list, description="Detected telemetry packages")
    env_vars: List[str] = Field(default_factory=list, description="Detected telemetry environment variables")
    tools_detected: List[str] = Field(default_factory=list, description="All observability tools/providers detected across manifests, env, and code")
    total_agents: int = 0
    instrumented_agents: int = 0
    total_tools: int = 0
    instrumented_tools: int = 0
    recommendations: List[str] = Field(default_factory=list, description="Observability gap analysis & recommendations")

    @computed_field
    @property
    def is_observability_configured(self) -> bool:
        return len(self.packages) > 0 or len(self.env_vars) > 0

    @computed_field
    @property
    def agent_instrumentation_pct(self) -> float:
        if self.total_agents == 0:
            return 100.0
        return round((self.instrumented_agents / self.total_agents) * 100, 1)


class ScanError(BaseModel):
    """Information about any file parsing errors encountered during the scan."""
    file_path: str
    error_type: str
    message: str


class ScanResult(BaseModel):
    """Aggregate result of a repository scan."""
    target_path: str
    files_scanned: int = 0
    python_files_count: int = 0
    scan_duration_ms: float = 0.0
    frameworks_detected: List[str] = Field(default_factory=list, description="List of detected agentic frameworks")
    graphs: List[GraphInfo] = Field(default_factory=list)
    agent_definitions: List[AgentDef] = Field(default_factory=list, description="All agent function definitions detected")
    tool_definitions: List[ToolDef] = Field(default_factory=list, description="All @tool functions detected")
    tool_nodes: List[ToolNodeDef] = Field(default_factory=list, description="All ToolNode instances detected")
    tools_bound: List[ToolsBoundInfo] = Field(default_factory=list, description="All tools binding calls detected")
    prompts: List[PromptDef] = Field(default_factory=list, description="All prompt definitions detected")
    import_sources: Dict[str, str] = Field(default_factory=dict, description="Imported symbols mapped to module/package")
    observability: Optional[ObservabilityAudit] = Field(default=None, description="Observability audit result")
    errors: List[ScanError] = Field(default_factory=list)

    @computed_field
    @property
    def total_graphs(self) -> int:
        return len(self.graphs)

    @computed_field
    @property
    def total_compiled(self) -> int:
        return sum(1 for g in self.graphs if g.is_compiled)

    @computed_field
    @property
    def total_nodes(self) -> int:
        return sum(len(g.nodes) for g in self.graphs)

    @computed_field
    @property
    def total_edges(self) -> int:
        return sum(len(g.edges) for g in self.graphs)

    def to_manifest(self) -> Any:
        """Converts ScanResult into the standardized Cohzen Manifest v0.1 specification."""
        from datetime import datetime, timezone
        from cz.manifest.schema import (
            CohzenManifest,
            CompilationDef,
            EdgeDef,
            GraphDef,
            ManifestMetadata,
            ModelDef as ManifestModelDef,
            NodeClassification,
            NodeDef as ManifestNodeDef,
            ResolutionDef,
            SourceLocation,
            ToolDef as ManifestToolDef,
        )

        manifest_tools: Dict[str, ManifestToolDef] = {}
        manifest_models: Dict[str, ManifestModelDef] = {}
        manifest_nodes: Dict[str, ManifestNodeDef] = {}
        manifest_graphs: List[GraphDef] = []

        # 1. Populate registered tools
        for t in self.tool_definitions:
            tool_id = f"tool.{t.name}"
            loc = SourceLocation(file=t.file_path, line_start=t.line_start, line_end=t.line_end) if t.file_path else None
            manifest_tools[tool_id] = ManifestToolDef(
                id=tool_id,
                name=t.name,
                source=loc,
                docstring=t.docstring,
                resolution=ResolutionDef(status="resolved"),
            )

        # 2. Populate graphs, nodes, and referenced models/tools
        for g in self.graphs:
            graph_id = f"graph.{g.graph_var}"
            node_ids_in_graph: List[str] = []

            for n in g.nodes:
                node_id = n.name
                node_ids_in_graph.append(node_id)

                # Identify referenced models
                node_model_ids: List[str] = []
                if n.agent_def:
                    for call in n.agent_def.llm_calls:
                        model_name_or_caller = call.model_name or call.caller_var or "default"
                        m_id = f"model.{call.provider}.{model_name_or_caller}"
                        if m_id not in node_model_ids:
                            node_model_ids.append(m_id)
                        if m_id not in manifest_models:
                            m_loc = SourceLocation(file=call.file_path, line_start=call.line_number, line_end=call.line_number) if call.file_path else None
                            manifest_models[m_id] = ManifestModelDef(
                                id=m_id,
                                provider=call.provider,
                                name=call.model_name or f"{call.caller_var}.{call.method}",
                                source=m_loc,
                            )

                # Identify referenced tools
                node_tool_ids: List[str] = []
                referenced_tool_names: List[str] = []
                if n.tool_node_def and n.tool_node_def.tools:
                    referenced_tool_names.extend(n.tool_node_def.tools)
                elif n.agent_def and n.agent_def.tools_bound:
                    referenced_tool_names.extend(n.agent_def.tools_bound)

                for t_name in referenced_tool_names:
                    t_id = f"tool.{t_name}"
                    if t_id not in node_tool_ids:
                        node_tool_ids.append(t_id)
                    if t_id not in manifest_tools:
                        pkg = self.import_sources.get(t_name)
                        if pkg:
                            tool_res = ResolutionDef(status="unresolved", reason="external_import", package=pkg)
                        else:
                            tool_res = ResolutionDef(status="unresolved", reason="missing_symbol")
                        manifest_tools[t_id] = ManifestToolDef(
                            id=t_id,
                            name=t_name,
                            source=None,
                            docstring=None,
                            resolution=tool_res,
                        )

                # Handler resolution
                if n.agent_def or n.tool_node_def:
                    resolution = ResolutionDef(status="resolved")
                elif n.handler in ("START", "END", "__start__", "__end__"):
                    resolution = ResolutionDef(status="resolved")
                elif "lambda" in n.handler:
                    # Lambda is an inline function definition, fully resolved
                    resolution = ResolutionDef(status="resolved")
                elif "<dynamic>" in n.handler:
                    resolution = ResolutionDef(status="partially_resolved", reason="dynamic_expression")
                elif n.handler in self.import_sources or n.name in self.import_sources:
                    pkg = self.import_sources.get(n.handler) or self.import_sources.get(n.name)
                    resolution = ResolutionDef(status="unresolved", reason="external_import", package=pkg)
                else:
                    resolution = ResolutionDef(status="unresolved", reason="external_import")

                # Optional heuristic classification (non-authoritative)
                classification = None
                evidence: List[str] = []
                if n.tool_node_def or "toolnode" in n.handler.lower():
                    evidence.append("tool_node_handler")
                    classification = NodeClassification(role="tool_node", confidence="high", evidence=evidence)
                elif n.agent_def:
                    if n.agent_def.llm_calls:
                        evidence.append("llm_invocation")
                    if n.agent_def.tools_bound:
                        evidence.append("tool_binding")
                    if "lambda" in n.handler:
                        evidence.append("inline_lambda")
                    role = "agent" if "llm_invocation" in evidence else "logic"
                    classification = NodeClassification(role=role, confidence="high", evidence=evidence)
                elif "lambda" in n.handler:
                    classification = NodeClassification(role="logic", confidence="high", evidence=["inline_lambda"])
                elif "router" in n.name.lower() or "route" in n.handler.lower():
                    classification = NodeClassification(role="router", confidence="medium", evidence=["naming_convention"])

                line_s = n.agent_def.line_start if n.agent_def else n.line_number
                line_e = n.agent_def.line_end if n.agent_def else n.line_number
                n_loc = SourceLocation(file=n.file_path, line_start=line_s, line_end=line_e) if n.file_path else None

                manifest_nodes[node_id] = ManifestNodeDef(
                    id=node_id,
                    name=n.name,
                    kind="node",
                    handler=n.handler,
                    source=n_loc,
                    model_ids=node_model_ids,
                    tool_ids=node_tool_ids,
                    prompts=list(n.agent_def.prompts_used) if n.agent_def else [],
                    resolution=resolution,
                    classification=classification,
                )

            # Edges
            m_edges: List[EdgeDef] = []
            for e in g.edges:
                e_loc = SourceLocation(file=e.file_path, line_start=e.line_number, line_end=e.line_number) if e.file_path else None
                m_edges.append(
                    EdgeDef(
                        source=e.source,
                        target=e.target,
                        edge_type=e.edge_type,
                        condition_fn=e.condition_fn,
                        conditional_mapping=e.conditional_mapping or None,
                        location=e_loc,
                    )
                )
            m_edges.sort(key=lambda x: (x.source, x.target, x.edge_type))

            # Compilation
            compilation_def = None
            if g.is_compiled and g.compile_info:
                c = g.compile_info
                c_loc = SourceLocation(file=c.file_path, line_start=c.line_number, line_end=c.line_number) if c.file_path else None
                compilation_def = CompilationDef(
                    compiled_var=c.compiled_var,
                    checkpointer=c.checkpointer,
                    interrupt_before=c.interrupt_before,
                    interrupt_after=c.interrupt_after,
                    store=c.store,
                    source=c_loc,
                )

            g_loc = SourceLocation(file=g.file_path, line_start=g.line_number, line_end=g.line_number) if g.file_path else None
            manifest_graphs.append(
                GraphDef(
                    id=graph_id,
                    name=g.graph_var,
                    framework=g.framework,
                    graph_class=g.graph_class,
                    state_schema=g.state_schema,
                    source=g_loc,
                    node_ids=node_ids_in_graph,
                    edges=m_edges,
                    compilation=compilation_def,
                )
            )

        # Deterministic sorting
        manifest_graphs.sort(key=lambda x: x.id)
        sorted_nodes = sorted(manifest_nodes.values(), key=lambda x: x.id)
        sorted_tools = sorted(manifest_tools.values(), key=lambda x: x.id)
        sorted_models = sorted(manifest_models.values(), key=lambda x: x.id)

        # External library dependencies vs genuinely missing / dynamic symbols
        external_nodes = [n for n in sorted_nodes if n.resolution.reason == "external_import"]
        external_tools = [t for t in sorted_tools if t.resolution.reason == "external_import"]
        external_imports_count = len(external_nodes) + len(external_tools)
        external_packages = sorted(list({
            x.resolution.package for x in (external_nodes + external_tools) if x.resolution.package
        }))

        # Analysis limitations and warnings
        unresolved_nodes_count = sum(1 for n in sorted_nodes if n.resolution.status == "unresolved")
        unresolved_tools_count = sum(1 for t in sorted_tools if t.resolution.status == "unresolved")
        total_unresolved = unresolved_nodes_count + unresolved_tools_count
        dynamic_count = sum(1 for n in sorted_nodes if n.resolution.status == "partially_resolved")

        warnings: List[str] = []
        if unresolved_nodes_count > 0:
            if external_packages:
                warnings.append(f"{unresolved_nodes_count} node handler(s) imported from external libraries ({', '.join(external_packages)}).")
            else:
                warnings.append(f"{unresolved_nodes_count} node handler(s) could not be statically resolved to local definitions (external imports).")
        if unresolved_tools_count > 0:
            warnings.append(f"{unresolved_tools_count} tool reference(s) lack local function definitions (external imports).")
        if dynamic_count > 0:
            warnings.append(f"{dynamic_count} dynamic node/tool expression(s) encountered.")
        if len(self.errors) > 0:
            warnings.append(f"{len(self.errors)} file(s) encountered syntax/parsing errors.")

        metadata = ManifestMetadata(
            target=self.target_path,
            files_scanned=self.files_scanned,
            files_skipped=0,
            parse_errors=len(self.errors),
            unresolved_symbols=total_unresolved,
            dynamic_constructions=dynamic_count,
            external_imports=external_imports_count,
            external_packages=external_packages,
            scan_duration_ms=round(self.scan_duration_ms, 2),
            created_at=datetime.now(timezone.utc).isoformat(),
            warnings=warnings,
        )

        return CohzenManifest(
            version="0.1.0",
            frameworks=self.frameworks_detected,
            graphs=manifest_graphs,
            nodes=sorted_nodes,
            tools=sorted_tools,
            models=sorted_models,
            metadata=metadata,
        )

