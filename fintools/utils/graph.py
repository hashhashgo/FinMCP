from __future__ import annotations

from typing import Callable, Dict, List, TypeAlias, Tuple, Any
import tqdm
import asyncio
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import StateNode, CompiledStateGraph

from langgraph.graph import MessagesState

ConditionalEdge = Callable[[MessagesState], str]
Sequence: TypeAlias = str | StateNode | Tuple[str, StateNode] | Tuple[str, str] | Tuple["Sequence", ConditionalEdge, Dict[str, "Sequence"], str] | List["Sequence"]
# Sequence: TypeAlias = _Sequence | List[StateNode] # PyLance has bug that needs this extra layer

def _unpack_sequence(
    workflow: StateGraph,
    sequence: Sequence,
    counter: Dict[str, int] = {}
) -> Tuple[str, str]:
    """Recursively unpacks a sequence into the StateGraph."""
    def get_node_name(node: StateNode) -> str:
        nonlocal counter
        qualname = node.__qualname__
        node_name = " ".join([name.capitalize() for name in qualname.split('.')[-1].split('_')])
        if node_name in counter:
            counter[node_name] += 1
            node_name = f"{node_name} #{counter[node_name]}"
        else:
            counter[node_name] = 1
        return node_name

    if isinstance(sequence, str):
        return (sequence, sequence)
    elif isinstance(sequence, tuple) and isinstance(sequence[0], str) and isinstance(sequence[1], str):
        return (sequence[0], sequence[1])
    elif callable(sequence) or (isinstance(sequence, tuple) and len(sequence) == 2):
        if isinstance(sequence, tuple):
            assert callable(sequence[1]), "If sequence is a tuple, the second element must be a callable StateNode."
            node = sequence[1]
            node_name = sequence[0]
        else:
            node = sequence
            node_name = get_node_name(sequence)
        workflow.add_node(node_name, node)
        return (node_name, node_name)
    elif isinstance(sequence, list):
        seqs = []
        for item in sequence:
            seqs.append(_unpack_sequence(
                workflow=workflow,
                sequence=item,
                counter=counter
            ))
        for i in range(len(seqs) - 1):
            workflow.add_edge(seqs[i][1], seqs[i + 1][0])
        return (seqs[0][0], seqs[-1][1])
    elif isinstance(sequence, tuple) and len(sequence) == 4:
        source_f, source_l = _unpack_sequence(
            workflow=workflow,
            sequence=sequence[0],
            counter=counter
        )
        path_map = {}
        final = source_l
        for con in sequence[2]:
            f, l = _unpack_sequence(
                workflow=workflow,
                sequence=sequence[2][con],
                counter=counter
            )
            path_map[con] = f
            workflow.add_edge(l, source_l)
            if con == sequence[3]:
                final = l
        workflow.add_conditional_edges(
            source = source_l,
            path = sequence[1],
            path_map = path_map
        )
        return (source_f, final)
    else:
        raise ValueError("Invalid sequence item.")

def sequence_to_workflow(
        sequence: Sequence,
        workflow: StateGraph | None = None,
        state_schema: type[MessagesState] | None = None,
    ) -> Tuple[StateGraph, Tuple[str, str]]:
    """Creates a sequential StateGraph with START and END nodes."""
    if workflow is None:
        assert state_schema is not None, "Either workflow or state_schema must be provided."
        workflow = StateGraph(state_schema)

    first_node, last_node = _unpack_sequence(
        workflow=workflow,
        sequence=sequence,
        counter={}
    )
    
    return workflow, (first_node, last_node)

async def run_with_retry(coro, max_retries=3, task_desc="anonymous task", logger=logging.getLogger(__name__)):
    retry_times = 0
    while retry_times < max_retries:
        try:
            result = await coro
            return result
        except Exception as e:
            logger.error(f"Error during {task_desc}: {e}. Retrying {retry_times + 1}/{max_retries}...")
            retry_times += 1
    raise Exception(f"Max retries exceeded for {task_desc}.")

async def limited(idx, coro, sem: asyncio.Semaphore): 
    async with sem:
        try:
            res = await coro
            return idx, res
        except Exception as e:
            return idx, e


async def batch_invoke(
    batch_states: list,
    graph: CompiledStateGraph,
    check_fn: Callable[[Any], bool] = lambda x: True,
    max_concurrent: int = 5,
    retry_times: int = 3,
    task_desc: str = "anonymous task",
    logger = logging.getLogger(__name__)
) -> Tuple[List[Tuple[int, dict]], List[dict]]:
    sem = asyncio.Semaphore(max_concurrent)
    retry_list = []
    coros = [
        asyncio.create_task(
            limited(idx, 
                run_with_retry(
                    graph.ainvoke(batch_state),
                    max_retries=retry_times,
                    task_desc=f"batch {idx} invocation for {task_desc}",
                    logger=logger
                ), sem
            )
        )
        for idx, batch_state in enumerate(batch_states)
    ]
    res_list = []
    for coro in tqdm.tqdm(asyncio.as_completed(coros), total=len(coros), desc=task_desc):
        idx, res = await coro
        if isinstance(res, Exception):
            logger.error(f"Error processing batch {idx}: {res}")
            retry_list.append(batch_states[idx])
        else:
            if not check_fn(res):
                retry_list.append(batch_states[idx])
            else:
                res_list.append((idx, res))
    return res_list, retry_list
