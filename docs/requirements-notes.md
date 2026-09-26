
# Requirements Notes

Kevin Daniel | 26 Sep 2026

My own notes written before starting the build. The detailed version is in REQUIREMENTS.md.

## Goal

Build employee salary management software for an organization with 10,000 employees.

## User Persona

HR Manager of the org.

## Problem Statement

Currently ACME org's HR team manages salary data for 10,000 employees across multiple countries, with everything managed via Excel, which is tedious. We want the HR manager to manage the salary data via web based software, and be able to answer questions about how the org pays people.

## Requirements

- Employee details along with department, country and job role.
- Salary details. Under salary details there will be bands, and the band depends on experience level, role and department.
- Since employees are in multiple countries, salary has to be stored in local currency. For comparison across countries I will also keep a normalized value.
- Salary changes should be kept as history instead of overwriting, otherwise we cannot answer how pay changed over time.

## Scope

- Paginated list to view all employees, with search and filters (department, country, level).
- Detailed view per employee, including current salary and past salary changes.
- Create / edit employee and salary.
- Salary bands should be viewable and editable.
- Some basic summary views so the HR manager can actually answer questions: headcount and average salary by department and by country, and employees paid outside their band.

## Out of Scope

- Payroll and payslip management. This is a compensation record system, not a payroll engine. Payroll needs country specific tax and statutory rules which is a much bigger problem than what is asked here.
- RBAC and multiple user roles. Only one persona is given (HR Manager), so a single login is enough. Roles can be added later without changing the data model.
- Bulk Excel / CSV import. A proper importer needs validation and partial failure handling, which is a project on its own. The seed script already proves bulk loading works.
- Leave, attendance, performance reviews, equity and benefits. Adjacent HR areas, not needed to answer how the org pays people.
- Salary forecasting and increment simulation. Would be useful but there is no real data to base it on. Noted as a v2 item.

## Assumptions

- No real data was provided, and the assessment asks for a seed script, so all data is generated (10,000 employees, 6 countries, 8 departments, 5 experience levels).
- Salary is annual gross (base + bonus) in the employee's local currency.
- An employee belongs to one department and one country at a time.

## Tech Stack

- Backend: Python with FastAPI. The JD mentions Python, FastAPI is my choice for validation and auto generated API docs.
- Database: MySQL. Data is relational and I need window functions for median and band comparison queries.
- Frontend: React with TypeScript.