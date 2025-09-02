# AI Code Review & Bug Fix Prompt

You are an expert software engineer conducting a thorough code review. Please analyze the provided codebase for bugs, code quality issues, and potential improvements with a strong emphasis on code conciseness and clarity.

## Project Context

- Project specifications are located in the `.kiro/` folder
- Steering documents and requirements are in `.kiro/steering/`
- Please reference these documents to understand the project's intended functionality and architecture

## STEP 1: Analysis Planning & Documentation

Before beginning the code review, create a comprehensive analysis plan:

### 1. Review Project Structure
- Examine the codebase organization
- Read all documents in `.kiro/steering/` to understand requirements
- Identify key components, modules, and dependencies

### 2. Create Analysis Plan Document
- Output a detailed analysis plan as a markdown file: `docs/code-review/analysis-plan-[YYYY-MM-DD].md`
- Include the following sections:
  - **Project Overview** (based on steering documents)
  - **Codebase Structure Analysis**
  - **Planned Review Areas** (prioritized list)
  - **Task Breakdown** with estimated effort
  - **Success Criteria** for the review

### 3. Task List Format
```markdown
## Analysis Tasks
- [ ] Review core module X for logic errors
- [ ] Check database interaction patterns
- [ ] Validate error handling consistency
- [ ] Performance analysis of critical paths
- [ ] Alignment check with specifications
- [ ] Code conciseness optimization review
```

### 🛑 CHECKPOINT
**Please review the analysis plan before I proceed with the actual code review. Confirm the approach aligns with your expectations.**

## STEP 2: Code Analysis (Execute after approval)

### Analysis Focus Areas

#### 1. Logic Errors & Bugs
- Incorrect conditional statements or loop logic
- Off-by-one errors in arrays/loops
- Null pointer exceptions and undefined variable access
- Race conditions and concurrency issues
- Memory leaks and resource management problems

#### 2. Performance Issues
- Inefficient algorithms or data structures
- Unnecessary database queries or API calls
- Memory-intensive operations
- Blocking operations on main threads

#### 3. Code Quality & Conciseness
- Dead or unreachable code
- Inconsistent error handling
- Missing edge case handling
- Poor variable naming and unclear logic flow
- **Verbose or repetitive code patterns**
- **Opportunities for code consolidation**
- **Unnecessary complexity that could be simplified**
- **Redundant functions or methods**
- **Overly nested conditional statements**
- **Long parameter lists that could be simplified**
- Adherence to project specifications in `.kiro/steering/`

#### 4. Code Conciseness Optimization
- **Replace verbose constructs with more concise alternatives**
- **Identify opportunities for utility functions to reduce duplication**
- **Suggest modern language features that reduce boilerplate**
- **Consolidate similar functions or classes**
- **Eliminate unnecessary intermediate variables**
- **Simplify complex expressions while maintaining readability**

### Response Format

For each issue found, provide:
- **Location:** File name and line number(s)
- **Issue Type:** Bug severity (Critical/High/Medium/Low) or Improvement opportunity
- **Description:** Clear explanation of the problem or optimization
- **Impact:** Potential consequences if left unfixed or benefits of optimization
- **Conciseness Impact:** How the change improves code brevity and clarity
- **Specification Alignment:** Does this align with requirements in `.kiro/steering/`?
- **Fix:** Specific code changes needed
- **Improved Code:** Show the more concise corrected version

### Final Deliverable

Create `docs/code-review/review-results-[YYYY-MM-DD].md` with:
- Summary of findings
- **Conciseness improvements summary with before/after LOC counts**
- Prioritized fix recommendations
- Implementation roadmap
- Updated task checklist with completion status

## Additional Instructions

- **Prioritize solutions that reduce code length without sacrificing readability**
- **Suggest refactoring patterns that eliminate code duplication**
- **Recommend modern language idioms that express intent more concisely**
- Prioritize critical bugs that could cause crashes or functionality failures
- Ensure fixes align with the project's specifications and steering documents
- Flag any deprecated dependencies or outdated patterns
- Consider the codebase's architecture against the intended design in specs
- Provide unit test suggestions for identified issues
- **Include metrics on code reduction (e.g., "Reduced 50 lines to 20 lines")**

Please be thorough but practical - focus on actionable improvements that genuinely enhance code quality, reliability, conciseness, and alignment with project specifications. Always balance brevity with maintainability and readability.