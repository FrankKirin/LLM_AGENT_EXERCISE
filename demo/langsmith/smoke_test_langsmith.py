from langsmith import Client

client = Client()

runs = list(
    client.list_runs(
        project_name="LS_DEBUG_TEST",
        limit=10,
    )
)

print("run count =", len(runs))

for run in runs:
    print(run.id, run.name, run.run_type)