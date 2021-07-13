from typing import Callable, Dict, Optional
from functools import partial
from .processors import Deduplicator, resize_batch, save_multiprocess
from .filters import get_filter_by_min_size
from .readers import get_image_reader
from connectors import Notificator, Statuses


def chain_functions(*functions) -> Callable:
    def func(*init_args, **init_kwargs):
        intermidiate_result = functions[0](*init_args, **init_kwargs)

        for next_function in functions[1:]:
            next_function(intermidiate_result)

        return intermidiate_result

    return func


def functional_graph(functions: Dict[str, Callable], graph: dict):
    def func(item, task_id):
        notificator = Notificator(list(functions.keys()), 'deduplication_result_1')
        backyard = {'task_id': task_id}
        node_outputs = {}

        for name in graph["names"]:
            notificator.update_status(name, Statuses.staged, task_id)

            inputs = {key: backyard[key] for key in graph["config"][name].get("inputs", [])}
            if graph["config"][name].get("task_id"):
                inputs["task_id"] = task_id

            notificator.update_status(name, Statuses.processing, task_id)
            # TODO make try/except block with  status updating

            if not len(inputs):  # input node in graph
                outputs = functions[name](item)
            elif "nullsrc" in graph["config"][name]:
                nullsrc_key = graph["config"][name]["nullsrc"]
                outputs = functions[name](*list(inputs.values()), **{nullsrc_key: item})
            else:
                outputs = functions[name](*list(inputs.values()))

            if not isinstance(outputs, tuple):
                outputs = (outputs,)

            for i, output_key in enumerate(graph["config"][name].get("outputs") or []):
                backyard[output_key] = outputs[i]

            # output node has no named outputs
            if not graph["config"][name].get("outputs", []):
                node_outputs[name] = outputs

            notificator.update_status(name, Statuses.successful, task_id)

        return node_outputs

    return func


def build_pipeline(
    filter_by_size: bool,
    need_resize: bool,
    deduplication: bool,
    save_path: str,
    filter_args: Optional[dict] = None,
    resize_args: Optional[dict] = None,
    deduplication_args: Optional[dict] = None,
    graph: Optional[dict] = None
):
    if filter_by_size:
        if not filter_args:
            raise AttributeError("If set flag filter_by_size you have to provide filter_args!")

        filter_func = get_filter_by_min_size(**filter_args)
    else:
        filter_func = None

    reader = get_image_reader(filter_func)

    processing_functions = [reader]

    if need_resize:
        if not resize_args:
            raise AttributeError("If set flag need_resize you have to provide resize_args!")

        resize_partial = partial(resize_batch, **resize_args)
        processing_functions.append(resize_partial)

    if deduplication:
        if not deduplication_args:
            raise AttributeError("If set flag deduplication you have to provide deduplication_args!")

        # TODO read pool_size from config
        deduplicator = Deduplicator('/storage1/mrowl/image_indexes', 8, create_new=True)
        deduplicate_partial = partial(deduplicator, **deduplication_args)
        processing_functions.append(deduplicate_partial)

    save_partial = partial(save_multiprocess, pool_size=8, storage_path=save_path)

    if graph:
        return functional_graph(
            {
                "read": reader,
                "resize": resize_partial,
                "deduplication": deduplicate_partial,
                "save": save_partial
            },
            graph
        )

    return chain_functions(*processing_functions)
