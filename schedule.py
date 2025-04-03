""" 
Implemenentation for the resource scheduling problem 
for Research 
"""

import pandas as pd
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus, lpSum,value, PULP_CBC_CMD
from typing import Final


EUROPEAN_HOURS: Final = 1720  # European working hours per year

import pandas as pd

# Load project data
df_projects = pd.read_csv("projects.csv")
df_projects.columns = df_projects.columns.str.strip()  # Remove unwanted spaces

# Extract **project names as strings**
projects = df_projects["ProjectName"].tolist()
funding = dict(zip(df_projects["ProjectName"], df_projects["Funding"]))  # Required FTEs per project
#total_resources = dict(zip(df_projects["ProjectName"], df_projects["TotalResources"]))  


# Load people data
df_people = pd.read_csv("people.csv")
df_people.columns = df_people.columns.str.strip()  # Remove unwanted spaces

# Extract **person names as strings**
people = df_people["PersonName"].tolist()
costs = dict(zip(df_people["PersonName"], df_people["Cost"])) 

# Extract **profile type  as strings**
profiles = dict(zip(df_people["PersonName"], df_people["Profile"]))  
#print(profiles)

# Load additional constraints from constraint.csv
df_constraints = pd.read_csv("constraints.csv")
df_constraints.columns = df_constraints.columns.str.strip()  # Clean column names



# Read the Project Roles CSV
# ================================
# Adjust delimiter if needed (here we assume tab-delimited)
df_project_roles = pd.read_csv("project_roles.csv")

# Rename the first column to 'Project' if not already named so
df_project_roles.rename(columns={df_project_roles.columns[0]: 'Project'}, inplace=True)

# Calculate total requested resources from project_roles.csv
total_requested_resources = {}
for project in df_project_roles['Project']:
    # Sum the role requirements for each project
    total_requested = df_project_roles.loc[df_project_roles['Project'] == project].iloc[:, 1:].sum(axis=1).values[0]
    total_requested_resources[project] = total_requested

print("Total requested resources per project:")
for project, total in total_requested_resources.items():
    print(f"Project '{project}': {total} hours")



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


def checkUnmatchedRoles():
    # Load data
    people_df = pd.read_csv("people.csv")
    roles_df = pd.read_csv("project_roles.csv", index_col=0)

    # Extract available profiles from people
    available_profiles = set(people_df["Profile"].unique())

    print("=== Role (Profile) Availability Check Per Project ===")
    for project, row in roles_df.iterrows():
        required_profiles = set(row[row > 0].index)  # Columns with effort > 0
        missing = required_profiles - available_profiles
        if missing:
            print(f"❌ Project '{project}' is missing profiles: {', '.join(missing)}")
        else:
            print(f"✅ Project '{project}' has all required profiles available.")

def checkEnoughResourcesForProfile():
    print("Checking whether enough resources are available for each profile")
    # Load data
    people = pd.read_csv("people.csv")
    project_roles = pd.read_csv("project_roles.csv")


    # Step 1: Calculate available hours per profile
    profile_counts = people['Profile'].value_counts()
    profile_hours_available = profile_counts * EUROPEAN_HOURS

    # Step 2: Calculate required hours per profile across all projects
    # Reshape project roles table
    project_role_needs = project_roles.melt(id_vars=['Project'], var_name='Role', value_name='HoursNeeded')
    project_role_needs = project_role_needs.dropna()

    # Group by Role to sum up required hours
    total_hours_required_per_role = project_role_needs.groupby('Role')['HoursNeeded'].sum()

    # Step 3: Combine into a single DataFrame
    resource_balance_df = pd.DataFrame({
        "Available Hours": profile_hours_available,
        "Required Hours": total_hours_required_per_role
    }).fillna(0)

    # Step 4: Compute surplus or shortage
    resource_balance_df["Surplus (Available - Required)"] = (
        resource_balance_df["Available Hours"] - resource_balance_df["Required Hours"]
    )

    # Show the result
    print(resource_balance_df)
    shortages = resource_balance_df[resource_balance_df["Surplus (Available - Required)"] < 0]
    if not shortages.empty:
        print("Insufficient availability for the following profiles:\n")
        print(shortages)

import pandas as pd


checkUnmatchedRoles()
checkEnoughResourcesForProfile()


# Define decision variables: Use actual names, not indexes
x = {(proj, person): LpVariable(f"x_{proj}_{person}", lowBound=0, upBound=EUROPEAN_HOURS, cat="Continuous")
     for proj in projects for person in people}

# Define the optimization problem
prob = LpProblem("Project_Allocation", LpMaximize)

# Objective function: Maximize total weighted cost
prob += lpSum(x[proj, person] * costs[person] * funding[proj] for proj in projects for person in people),"Maximize_Cost"

# Constraints

# Ensure each project gets the required hours (funding requirement)
for proj in projects:
    prob += lpSum(x[proj, person]  for person in people) <= total_requested_resources[proj], f"Capacity_per_project_{proj}"

# Ensure each person is not overassigned
for person in people:
    prob += lpSum(x[proj, person] for proj in projects) <= 1.5 * EUROPEAN_HOURS, f"Capacity_per_person_{person}_{hash(person)}"

#  Apply custom constraints from constraint.csv
for _, row in df_constraints.iterrows():
    proj = row["ProjectName"]
    person = row["PersonName"]
    constraint_value = row["ConstraintValue"]  # Extract the constraint number

    if proj in projects and person in people:
        try:
            constraint_value = float(constraint_value)  # Convert to float
        except ValueError:
            print(f"Warning: Invalid constraint value '{row['ConstraintValue']}' for {proj}-{person}")
            continue  # Skip invalid values
        if constraint_value == 0:
            # If the value is 0, enforce that x[proj, person] must be 0, i.e. not working on the project
            #prob += x[proj, person] == 0, f"Force_Zero_{proj}_{person}"
            continue
        else:
            # If the value is greater than 0, enforce x[proj, person] >= constraint_value
            prob += x[proj, person] >= constraint_value, f"Min_Constraint_{proj}_{person}"

#print(project_requirements)
#print(profiles)


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
    print("FTE Allocation matrix")
    print(fte_matrix)
    fte_matrix.to_csv("fte_matrix.csv",index=True)
    print("FTE allocation saved to 'fte_matrix.csv'")

    allocation_records = []

    for proj in projects:
        for person in people:
            hours = x[proj, person].varValue
            if hours and hours > 0:
                allocation_records.append({
                    "Project": proj,
                    "Person": person,
                    "HoursAllocated": round(hours, 2)
                })

    allocation_df = pd.DataFrame(allocation_records)
    print("Detailed allocation list:")
    print(allocation_df)

    allocation_df.to_csv("fte_allocation_detailed.csv", index=False)
    print("Three-column format saved to 'fte_allocation_detailed.csv'")     
