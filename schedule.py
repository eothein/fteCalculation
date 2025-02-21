""" 
Implemenentation for the resource scheduling problem 
for Research 
"""

import pandas as pd
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus, lpSum, PULP_CBC_CMD
from typing import Final

EUROPEAN_HOURS: Final = 1720  # European working hours per year

# Load project data
df_projects = pd.read_csv("projects.csv")
df_projects.columns = df_projects.columns.str.strip()  # Remove unwanted spaces

# Extract **project names as strings**
projects = df_projects["ProjectName"].tolist()
funding = dict(zip(df_projects["ProjectName"], df_projects["Funding"]))  # Required FTEs per project
total_resources = dict(zip(df_projects["ProjectName"], df_projects["TotalResources"]))  

# Load people data
df_people = pd.read_csv("people.csv")
df_people.columns = df_people.columns.str.strip()  # Remove unwanted spaces

# Extract **person names as strings**
people = df_people["PersonName"].tolist()
costs = dict(zip(df_people["PersonName"], df_people["Cost"])) 

# Extract **profile type  as strings**
profiles = dict(zip(df_people["PersonName"], df_people["profile"]))  
#print(profiles)

# Load additional constraints from constraint.csv
df_constraints = pd.read_csv("constraints.csv")
df_constraints.columns = df_constraints.columns.str.strip()  # Clean column names

# Define decision variables: Use actual names, not indexes
x = {(proj, person): LpVariable(f"x_{proj}_{person}", lowBound=0, upBound=EUROPEAN_HOURS, cat="Continuous")
     for proj in projects for person in people}

# Read the Project Roles CSV
# ================================
# Adjust delimiter if needed (here we assume tab-delimited)
df_project_roles = pd.read_csv("project_roles.csv")

# Rename the first column to 'Project' if not already named so
df_project_roles.rename(columns={df_project_roles.columns[0]: 'Project'}, inplace=True)

# Build a dictionary: project name -> { role: required_hours }
project_requirements = {}

for _, row in df_project_roles.iterrows():
    project_name = row['Project'].strip()  # Clean up any extra spaces
    role_hours = {}
    # Iterate over the role columns (all columns except the first)
    for role in df_project_roles.columns[1:]:
        # Remove any extra spaces from the role name
        role_clean = role.strip()
        value = row[role]
        # Try converting to float; if conversion fails (empty or non-numeric), treat as 0
        try:
            hours = float(value)
        except (ValueError, TypeError):
            hours = 0
        if hours > 0:
            role_hours[role_clean] = hours
    project_requirements[project_name] = role_hours

#print(project_requirements)


#print(x)

# Define the optimization problem
prob = LpProblem("Project_Allocation", LpMaximize)

# Objective function: Maximize total weighted cost
prob += lpSum(x[proj, person] * costs[person] * funding[proj] for proj in projects for person in people),"Maximize_Cost"

# Constraints

# Ensure each project gets the required FTEs (funding requirement)
for proj in projects:
    prob += lpSum(x[proj, person]  for person in people) == total_resources[proj], f"Capacity_per_project_{proj}"

# Ensure each person is not overassigned
for person in people:
    prob += lpSum(x[proj, person] for proj in projects) <= EUROPEAN_HOURS, f"Capacity_per_person_{person}_{hash(person)}"

#  Apply custom constraints from constraint.csv
for _, row in df_constraints.iterrows():
    proj = row["ProjectName"]
    person = row["PersonName"]
    constraint_value = row["ConstraintValue"]  # Extract the constraint number
    print(constraint_value)

    if proj in projects and person in people:
        try:
            constraint_value = float(constraint_value)  # Convert to float
        except ValueError:
            print(f"Warning: Invalid constraint value '{row['ConstraintValue']}' for {proj}-{person}")
            continue  # Skip invalid values
        if constraint_value == 0:
            # If the value is 0, enforce that x[proj, person] must be 0, i.e. not working on the project
            prob += x[proj, person] == 0, f"Force_Zero_{proj}_{person}"
        else:
            # If the value is greater than 0, enforce x[proj, person] >= constraint_value
            prob += x[proj, person] >= constraint_value, f"Min_Constraint_{proj}_{person}"

print(project_requirements)
print(profiles)


# ----------------------------
# Minimum Hours per Profile/Role for Each Project
# ----------------------------
# For each project in the requirements, enforce that the sum of the hours
# allocated to people with a given profile is at least the required hours.
for proj in projects:
    # Check if this project has defined role requirements
    if proj in project_requirements:
        for role, required_hours in project_requirements[proj].items():
            # List all persons whose profile matches the required role.
            persons_with_role = [person for person in people if profiles.get(person, "").strip() == role]
            if persons_with_role:
                constraint_name = f"Min_Profile_{proj}_{role}"
                prob += lpSum(x[proj, person] for person in persons_with_role) >= required_hours, constraint_name
            else:
                print(f"Warning: No person with profile '{role}' found for project '{proj}'.")



prob.writeLP("FTEModel.lp")

total_resources = sum(total_resources.values())
print(f"Total Resources to allocate: {total_resources}")
total_resources_to_spend = len(set(people)) * EUROPEAN_HOURS
print(f"Max Resources to spend: {total_resources_to_spend}")

if(total_resources_to_spend < total_resources):
    print(f"Warning: total resources to spend is less than total resources required")


# Solve the problem
prob.solve(PULP_CBC_CMD(msg=False))

print(f"Solver Status: {LpStatus[prob.status]}")

if(LpStatus[prob.status] == "Optimal"):
    print("Optimal Solution")
    fte_matrix = pd.DataFrame(0,index=projects, columns=people)
    for proj in projects:
        for person in people:
            fte_matrix.at[proj,person] = x[proj,person].varValue
    fte_matrix = fte_matrix.loc[:, (fte_matrix > 0).any(axis=0)]
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