""" 
Implemenentation for the resource scheduling problem 
for Research 
"""

import pandas as pd
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus, lpSum, PULP_CBC_CMD

# Load project data
df_projects = pd.read_csv("projects.csv")
df_projects.columns = df_projects.columns.str.strip()  # Remove unwanted spaces

# Extract **project names as strings**
projects = df_projects["ProjectName"].tolist()
funding = dict(zip(df_projects["ProjectName"], df_projects["Funding"]))  # Required FTEs per project
total_resources = dict(zip(df_projects["ProjectName"], df_projects["TotalResources"]))  # Max FTEs

# Load people data
df_people = pd.read_csv("people.csv")
df_people.columns = df_people.columns.str.strip()  # Remove unwanted spaces

# Extract **person names as strings**
people = df_people["PersonName"].tolist()
costs = dict(zip(df_people["PersonName"], df_people["Cost"]))  # Cost per person

# ✅ Define decision variables: Use actual names, not indexes
x = {(proj, person): LpVariable(f"x_{proj}_{person}", lowBound=0, upBound=1, cat="Continuous")
     for proj in projects for person in people}

print(x)

# Define the optimization problem
prob = LpProblem("Project_Allocation", LpMaximize)

# Objective function: Maximize total weighted cost
prob += lpSum(x[proj, person] * costs[person] * funding[proj] for proj in projects for person in people),"Maximize_Cost"

# Constraints

# Ensure each project gets the required FTEs (funding requirement)
for proj in projects:
    prob += lpSum(x[proj, person] * 12  for person in people) == total_resources[proj], f"Capacity_per_project_{proj}"

# Ensure each person is not overassigned
for person in people:
    prob += lpSum(x[proj, person] for proj in projects) <= 1, f"Capacity_per_person_{person}"

prob.writeLP("FTEModel.lp")

# Solve the problem
prob.solve(PULP_CBC_CMD(msg=False))

print(f"Solver Status: {LpStatus[prob.status]}")

if(LpStatus[prob.status] == "Optimal"):
    print("Optimal Solution")
    fte_matrix = pd.DataFrame(0,index=projects, columns=people)
    for proj in projects:
        for person in people:
            fte_matrix.at[proj,person] = x[proj,person].varValue
    print("\FTE Allocation matrix")
    print(fte_matrix)
    fte_matrix.to_csv("fte_matrix.csv",index=True)
    print("\FTE allocation saved to 'fte_matrix.csv'")

            
''''
# Print results
print("\nProject Assignments (Fractional FTEs):")
for proj in projects:
    assigned_people = [(person, round(x[proj, person].varValue, 2)) for person in people if x[proj, person].varValue > 0]
    if assigned_people:
        print(f"{proj}: " + ", ".join(f"{person} ({fte})" for person, fte in assigned_people))
'''