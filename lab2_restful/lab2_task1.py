from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app=FastAPI( )

polls = {}
votes = {}

# create poll
# vote
# get poll results
# delete your vote

class Poll(BaseModel):
    id: int
    question: str
    options: List[str]

class UserVote(BaseModel):
    user_id: int
    poll_id: int
    option: str


@app.post("/v1/items")
async def create_poll(poll: Poll):
    polls[poll.id] = poll
    votes[poll.id] = {}
    return poll

@app.post("/v1/items/{poll_id}/vote")
async def vote(poll_id: int, user_id: int,  option: str):
    votes[poll_id][user_id] = option
    return {"message": f"Vote for user {user_id} in poll {poll_id} recorded."}


@app.get("/v1/items/{poll_id}/results")
async def get_poll_results(poll_id: int):
    results = {opt: 0 for opt in polls[poll_id].options}
    for chosen_option in votes[poll_id].values():
        if chosen_option in results:
            results[chosen_option] += 1

    return {"poll_id": poll_id, "results": results}

@app.delete("/v1/items/{poll_id}/vote")
async def delete_vote(poll_id: int, user_id: int):
    votes[poll_id].pop(user_id, None)
    return {"message": f"Vote for user {user_id} in poll {poll_id} deleted."}