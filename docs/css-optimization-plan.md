# CSS File Structure Optimization Plan

## Current State Analysis

### File Sizes (lines of code)
- `security-extracted.css`: 2,750 lines (largest file)
- `admin-extracted.css`: 1,797 lines
- `style.css`: 1,611 lines
- `components.css`: 1,458 lines
- `utilities.css`: 352 lines

### Identified Issues

1. **Duplicate CSS Variables**: Multiple files define similar CSS variables
2. **Redundant Utility Classes**: Margin/padding utilities duplicated across files
3. **Similar Progress Bar Classes**: Different naming conventions for similar functionality
4. **Overlapping Display Utilities**: Multiple definitions of hidden/visible classes
5. **Inconsistent Icon Sizing**: Different approaches to icon sizing across files

## Optimization Strategy

### 1. Consolidate CSS Variables
- Move all CSS variables to a single `css-variables.css` file
- Remove duplicate variable definitions
- Standardize variable naming conventions

### 2. Merge Utility Classes
- Consolidate all utility classes into `utilities.css`
- Remove duplicates from `security-extracted.css` and `components.css`
- Standardize utility class naming

### 3. Optimize Progress Bar Classes
- Create unified progress bar system in `components.css`
- Remove redundant progress bar definitions
- Use consistent naming convention

### 4. Streamline Display Utilities
- Keep only one set of display utilities in `utilities.css`
- Remove duplicates from other files

### 5. Consolidate Icon Classes
- Create unified icon sizing system
- Remove duplicate icon classes

## Implementation Plan

### Phase 1: Create CSS Variables File
### Phase 2: Consolidate Utilities
### Phase 3: Optimize Components
### Phase 4: Remove Duplicates
### Phase 5: Update File Includes

## Expected Benefits
- Reduced total CSS file size by ~20-30%
- Improved maintainability
- Faster loading times
- Consistent styling patterns