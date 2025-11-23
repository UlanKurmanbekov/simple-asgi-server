from fastapi import FastAPI, HTTPException

app = FastAPI()

tasks = {}
count = 0


@app.get('/', response_model=dict)
async def get_tasks():
    return tasks


@app.post('/', status_code=201)
async def create_task(val: str):
    global count
    count += 1
    tasks[count] = val
    return {"id": count, "value": val}


@app.get('/{task_id}', response_model=str)
async def get_task(task_id: int):
    task = tasks.get(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail='Task not found')

    return task


@app.patch('/{task_id}', response_model=str)
async def update_task(task_id: int, new_val: str):
    task = tasks.get(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail='Task not found')

    tasks[task_id] = new_val
    return tasks[task_id]


@app.delete('/{task_id}', response_model=str)
async def delete_task(task_id: int):
    task = tasks.get(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail='Task not found')

    return tasks.pop(task_id)
