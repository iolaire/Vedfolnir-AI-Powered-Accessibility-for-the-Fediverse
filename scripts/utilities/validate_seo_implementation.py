# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
SEO Implementation Validation Script

This script validates that the landing page SEO metadata and structured data
are properly implemented according to the requirements.
"""

import requests
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def validate_seo_implementation(base_url="http://127.0.0.1:5000"):
    """
    Validate SEO implementation on the landing page
    
    Args:
        base_url (str): Base URL of the application
        
    Returns:
        dict: Validation results
    """
    print(f"🔍 Validating SEO implementation at {base_url}")
    
    try:
        # Get the landing page
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = {
            'success': True,
            'errors': [],
            'warnings': [],
            'validations': {}
        }
        
        # Requirement 7.1: Meta title tag
        title_tag = soup.find('title')
        if title_tag and 'Vedfolnir' in title_tag.text and 'AI-Powered Accessibility' in title_tag.text:
            results['validations']['meta_title'] = '✅ PASS'
        else:
            results['validations']['meta_title'] = '❌ FAIL'
            results['errors'].append("Meta title tag missing or incomplete")
        
        # Requirement 7.2: Meta description tag
        description_tag = soup.find('meta', attrs={'name': 'description'})
        if description_tag:
            desc_content = description_tag.get('content', '')
            if 120 <= len(desc_content) <= 200 and 'alt text' in desc_content.lower():
                results['validations']['meta_description'] = '✅ PASS'
            else:
                results['validations']['meta_description'] = '⚠️  WARNING'
                results['warnings'].append(f"Meta description length: {len(desc_content)} chars (optimal: 120-200)")
        else:
            results['validations']['meta_description'] = '❌ FAIL'
            results['errors'].append("Meta description tag missing")
        
        # Requirement 7.3: Open Graph tags
        og_tags = {
            'og:title': soup.find('meta', attrs={'property': 'og:title'}),
            'og:description': soup.find('meta', attrs={'property': 'og:description'}),
            'og:type': soup.find('meta', attrs={'property': 'og:type'}),
            'og:url': soup.find('meta', attrs={'property': 'og:url'}),
            'og:image': soup.find('meta', attrs={'property': 'og:image'})
        }
        
        missing_og_tags = [tag for tag, element in og_tags.items() if not element]
        if not missing_og_tags:
            results['validations']['open_graph'] = '✅ PASS'
        else:
            results['validations']['open_graph'] = '❌ FAIL'
            results['errors'].append(f"Missing Open Graph tags: {', '.join(missing_og_tags)}")
        
        # Twitter Card tags
        twitter_tags = {
            'twitter:card': soup.find('meta', attrs={'name': 'twitter:card'}),
            'twitter:title': soup.find('meta', attrs={'name': 'twitter:title'}),
            'twitter:description': soup.find('meta', attrs={'name': 'twitter:description'}),
            'twitter:image': soup.find('meta', attrs={'name': 'twitter:image'})
        }
        
        missing_twitter_tags = [tag for tag, element in twitter_tags.items() if not element]
        if not missing_twitter_tags:
            results['validations']['twitter_cards'] = '✅ PASS'
        else:
            results['validations']['twitter_cards'] = '❌ FAIL'
            results['errors'].append(f"Missing Twitter Card tags: {', '.join(missing_twitter_tags)}")
        
        # Requirement 7.4: Structured data markup
        json_ld_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
        structured_data_types = []
        
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and '@type' in data:
                    structured_data_types.append(data['@type'])
            except (json.JSONDecodeError, TypeError):
                continue
        
        required_types = ['SoftwareApplication', 'Organization', 'WebSite']
        missing_types = [t for t in required_types if t not in structured_data_types]
        
        if not missing_types:
            results['validations']['structured_data'] = '✅ PASS'
        else:
            results['validations']['structured_data'] = '❌ FAIL'
            results['errors'].append(f"Missing structured data types: {', '.join(missing_types)}")
        
        # Requirement 7.5: Heading hierarchy
        h1_tags = soup.find_all('h1')
        h2_tags = soup.find_all('h2')
        h3_tags = soup.find_all('h3')
        
        if len(h1_tags) == 1 and len(h2_tags) >= 2 and len(h3_tags) >= 1:
            h1_text = h1_tags[0].get_text()
            if 'Vedfolnir' in h1_text and 'AI-Powered Accessibility' in h1_text:
                results['validations']['heading_hierarchy'] = '✅ PASS'
            else:
                results['validations']['heading_hierarchy'] = '❌ FAIL'
                results['errors'].append("H1 tag missing required keywords")
        else:
            results['validations']['heading_hierarchy'] = '❌ FAIL'
            results['errors'].append(f"Invalid heading structure: H1={len(h1_tags)}, H2={len(h2_tags)}, H3={len(h3_tags)}")
        
        # Requirement 7.6: Keywords naturally integrated
        page_text = soup.get_text().lower()
        required_keywords = [
            'accessibility', 'alt text', 'ai-powered', 'activitypub',
            'mastodon', 'pixelfed', 'digital inclusion', 'fediverse'
        ]
        
        missing_keywords = [kw for kw in required_keywords if kw not in page_text]
        if not missing_keywords:
            results['validations']['keyword_integration'] = '✅ PASS'
        else:
            results['validations']['keyword_integration'] = '❌ FAIL'
            results['errors'].append(f"Missing keywords: {', '.join(missing_keywords)}")
        
        # Additional SEO checks
        robots_tag = soup.find('meta', attrs={'name': 'robots'})
        canonical_link = soup.find('link', attrs={'rel': 'canonical'})
        viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
        
        additional_checks = {
            'robots_meta': robots_tag is not None,
            'canonical_link': canonical_link is not None,
            'viewport_meta': viewport_tag is not None
        }
        
        passed_additional = sum(additional_checks.values())
        results['validations']['additional_seo'] = f"✅ {passed_additional}/3 additional SEO elements"
        
        # Overall success
        if results['errors']:
            results['success'] = False
        
        return results
        
    except requests.RequestException as e:
        return {
            'success': False,
            'errors': [f"Failed to connect to {base_url}: {e}"],
            'warnings': [],
            'validations': {}
        }
    except Exception as e:
        return {
            'success': False,
            'errors': [f"Validation error: {e}"],
            'warnings': [],
            'validations': {}
        }


def print_validation_results(results):
    """Print validation results in a formatted way"""
    print("\n" + "="*60)
    print("SEO IMPLEMENTATION VALIDATION RESULTS")
    print("="*60)
    
    # Print validation results
    for check, result in results['validations'].items():
        print(f"{check.replace('_', ' ').title():<25} {result}")
    
    print("\n" + "-"*60)
    
    # Print errors
    if results['errors']:
        print("❌ ERRORS:")
        for error in results['errors']:
            print(f"   • {error}")
        print()
    
    # Print warnings
    if results['warnings']:
        print("⚠️  WARNINGS:")
        for warning in results['warnings']:
            print(f"   • {warning}")
        print()
    
    # Overall result
    if results['success']:
        print("🎉 OVERALL RESULT: SEO implementation is VALID!")
    else:
        print("💥 OVERALL RESULT: SEO implementation has ISSUES that need to be fixed.")
    
    print("="*60)


def main():
    """Main validation function"""
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
    
    results = validate_seo_implementation(base_url)
    print_validation_results(results)
    
    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)


if __name__ == "__main__":
    main()