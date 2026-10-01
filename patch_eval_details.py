with open("backend/app/api/v1/eval.py", "r", encoding="utf-8") as f:
    text = f.read()

# Let's revert the previous change and do manual join
old_res = """    # Load results along with examples
    from sqlalchemy.orm import selectinload
    res_query = select(EvalResult).options(selectinload(EvalResult.example)).where(EvalResult.run_id == run.id)
    res_result = await db.execute(res_query)
    results = res_result.scalars().all()"""

new_res = """    res_query = select(EvalResult, EvalExample).join(EvalExample, EvalResult.example_id == EvalExample.id).where(EvalResult.run_id == run.id)
    res_result = await db.execute(res_query)
    results_and_examples = res_result.all()"""

old_dict = """        "results": [
            {
                "example_id": str(res.example_id),
                "input_prompt": res.example.input_prompt if getattr(res, "example", None) else "Unknown",
                "expected_tools": res.example.expected_tools if getattr(res, "example", None) else [],
                "actual_output": res.actual_output,
                "passed": res.passed,
                "tools_used": res.tools_used,
                "error_message": res.error_message,
                "latency_ms": res.latency_ms
            } for res in results
        ]"""

new_dict = """        "results": [
            {
                "example_id": str(res.id),
                "input_prompt": ex.input_prompt,
                "expected_tools": ex.expected_tools,
                "actual_output": res.actual_output,
                "passed": res.passed,
                "tools_used": res.tools_used,
                "error_message": res.error_message,
                "latency_ms": res.latency_ms
            } for res, ex in results_and_examples
        ]"""

if old_res in text:
    text = text.replace(old_res, new_res)
    text = text.replace(old_dict, new_dict)
    with open("backend/app/api/v1/eval.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched eval.py details join")
else:
    print("Could not find block")
