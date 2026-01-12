
"""
LaTeX to Speech Converter (ISS-022)

Converts LaTeX mathematical notation to speakable text for TTS.
This ensures narration reads naturally instead of saying "$h$" as "dollar h dollar".

Applied BEFORE sending text to Narakeet TTS API.
"""

import re


def latex_to_speech(text: str) -> str:
    """Convert LaTeX notation in text to speakable words.
    
    Examples:
        $h$ -> "h"
        $x^2$ -> "x squared"
        \\frac{1}{2} -> "one half"
        \\sqrt{x} -> "square root of x"
    """
    if not text:
        return text
    
    result = text
    
    # 1. Handle explicit inline math $...$
    result = _convert_inline_math(result)
    
    # 2. Handle plain text math (Greek, simple powers, equations)
    result = _handle_plain_text_math(result)

    # 3. Clean up generic LaTeX artifacts
    result = _clean_remaining_latex(result)
    
    # 4. Convert Numbers to Words (New Step)
    result = _handle_numbers(result)

    # 5. Collapse whitespace
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result


def _convert_inline_math(text: str) -> str:
    """Convert $...$ inline math to spoken text."""
    
    def replace_math(match):
        content = match.group(1)
        return _latex_to_words(content)
    
    # Handles $equation$
    result = re.sub(r'\$([^$]+)\$', replace_math, text)
    return result


def _handle_plain_text_math(text: str) -> str:
    """Handle math that isn't wrapped in LaTeX delimiters."""
    result = text
    
    # 0. Unicode Replacements (Crucial for copy-pasted math)
    unicode_map = {
        '−': '-',       # Unicode minus -> standard hyphen
        '±': ' plus or minus ',
        '×': ' times ',
        '÷': ' divided by ',
        '≤': ' less than or equal to ',
        '≥': ' greater than or equal to ',
        '≠': ' not equal to ',
        '≈': ' approximately ',
        '≡': ' equivalent to ',
        '∞': ' infinity ',
        '∫': ' integral of ',
        '√': ' square root of '
    }
    for char, replacement in unicode_map.items():
        result = result.replace(char, replacement)

    # 1. Greek characters (Direct replacement)
    greek_map = {
        'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta', 'ε': 'epsilon',
        'θ': 'theta', 'λ': 'lambda', 'μ': 'mu', 'π': 'pi', 'σ': 'sigma',
        'ω': 'omega', 'φ': 'phi', 'ψ': 'psi', 'ρ': 'rho', 'τ': 'tau',
        'Δ': 'Delta', 'Σ': 'Sigma', 'Ω': 'Omega'
    }
    for char, name in greek_map.items():
        result = result.replace(char, f" {name} ")

    # 2. Spacing around operators (for better TTS rhythm)
    # Ensure + and = have spaces if they are between alphanumeric chars
    result = re.sub(r'([a-zA-Z0-9])\+([a-zA-Z0-9])', r'\1 plus \2', result)
    result = re.sub(r'([a-zA-Z0-9])\-([a-zA-Z0-9])', r'\1 minus \2', result)
    result = re.sub(r'([a-zA-Z0-9])=([a-zA-Z0-9])', r'\1 equals \2', result)
    
    # Generic cleanup for standalone operators
    result = re.sub(r'\s*=\s*', ' equals ', result)
    result = re.sub(r'\s*\+\s*', ' plus ', result)
    # Don't replace hyphen in words (like "plus-minus"), only strict math context if possible
    # But for safety in this math-heavy context, we can be aggressive with isolated hyphens
    
    # 3. Powers (Relaxed matching)
    # Handle x2, a2, b2 inside longer strings (like ax2)
    # Logic: Letter followed by 2, not followed by other numbers
    result = re.sub(r'([a-zA-Z])2(?![0-9])', r'\1 squared', result)
    result = re.sub(r'([a-zA-Z])3(?![0-9])', r'\1 cubed', result)

    # 4. Calculus Notation
    result = re.sub(r'\bdydx\b', 'dy by dx', result)
    result = re.sub(r'\bddx\b', 'd by dx', result)
    
    return result


def _handle_numbers(text: str) -> str:
    """Convert digits to words: 12 -> twelve, 45 -> forty-five."""
    def num_replacer(match):
        return _num2words(int(match.group(0)))
    
    
    # 0. Pre-process: Separate digits from letters (e.g., 2x -> 2 x)
    # This prevents "twox" output which sounds wrong.
    # Note: We don't separate letter-digit (x2) because that was handled by power logic earlier,
    # and if any remain like 'v2', 'v two' is acceptable.
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)

    # Replace ALL numbers (even inside words like 2x -> two x)
    # Note: We must be careful not to break latex commands if any remain, 
    # but at this stage most should be gone or processed.
    return re.sub(r'\d+', num_replacer, text)


def _num2words(n: int) -> str:
    """Simple number to words converter for English."""
    if n == 0: return "zero"
    
    units = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    
    if n < 10: return units[n]
    if n < 20: return teens[n-10]
    if n < 100: return tens[n // 10] + ("-" + units[n % 10] if n % 10 != 0 else "")
    if n < 1000: return units[n // 100] + " hundred" + (" " + _num2words(n % 100) if n % 100 != 0 else "")
    if n < 1000000: return _num2words(n // 1000) + " thousand" + (" " + _num2words(n % 1000) if n % 1000 != 0 else "")
    
    return str(n) # Fallback for very large numbers


def _latex_to_words(latex: str) -> str:
    """Convert a LaTeX expression to spoken words."""
    result = latex.strip()
    
    common_fractions = {
        r'\\frac\s*\{1\}\s*\{2\}': 'one half',
        r'\\frac\s*\{1\}\s*\{3\}': 'one third',
        r'\\frac\s*\{2\}\s*\{3\}': 'two thirds',
        r'\\frac\s*\{1\}\s*\{4\}': 'one quarter',
        r'\\frac\s*\{3\}\s*\{4\}': 'three quarters',
        r'\\frac\s*\{1\}\s*\{5\}': 'one fifth',
        r'\\frac\s*\{1\}\s*\{6\}': 'one sixth',
        r'\\frac\s*\{1\}\s*\{8\}': 'one eighth',
        r'\\frac\s*\{1\}\s*\{10\}': 'one tenth',
    }
    
    for pattern, replacement in common_fractions.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    def general_frac(match):
        num = match.group(1).strip()
        denom = match.group(2).strip()
        num_spoken = _latex_to_words(num)
        denom_spoken = _latex_to_words(denom)
        return f"{num_spoken} over {denom_spoken}"
    
    result = re.sub(r'\\frac\s*\{([^}]+)\}\s*\{([^}]+)\}', general_frac, result)
    
    power_words = {
        '2': 'squared',
        '3': 'cubed',
    }
    
    def power_replace(match):
        base = match.group(1).strip()
        exp = match.group(2).strip()
        base_spoken = _latex_to_words(base) if '\\' in base else base
        if exp in power_words:
            return f"{base_spoken} {power_words[exp]}"
        else:
            exp_spoken = _latex_to_words(exp) if '\\' in exp else exp
            return f"{base_spoken} to the power of {exp_spoken}"
    
    # Matches x^{2} and x^2
    result = re.sub(r'([a-zA-Z0-9]+)\s*\^\s*\{([^}]+)\}', power_replace, result)
    result = re.sub(r'([a-zA-Z0-9]+)\s*\^\s*([0-9])', power_replace, result)
    
    def sqrt_replace(match):
        content = match.group(1).strip()
        content_spoken = _latex_to_words(content) if '\\' in content else content
        return f"square root of {content_spoken}"
    
    result = re.sub(r'\\sqrt\s*\{([^}]+)\}', sqrt_replace, result)
    
    greek_letters = [
        ('\\alpha', 'alpha'),
        ('\\beta', 'beta'),
        ('\\gamma', 'gamma'),
        ('\\delta', 'delta'),
        ('\\epsilon', 'epsilon'),
        ('\\theta', 'theta'),
        ('\\lambda', 'lambda'),
        ('\\mu', 'mu'),
        ('\\pi', 'pi'),
        ('\\sigma', 'sigma'),
        ('\\omega', 'omega'),
        ('\\phi', 'phi'),
        ('\\psi', 'psi'),
        ('\\rho', 'rho'),
        ('\\tau', 'tau'),
        ('\\eta', 'eta'),
        ('\\zeta', 'zeta'),
        ('\\nu', 'nu'),
        ('\\xi', 'xi'),
        ('\\chi', 'chi'),
        ('\\Delta', 'Delta'),
        ('\\Sigma', 'Sigma'),
        ('\\Pi', 'Pi'),
        ('\\Omega', 'Omega'),
    ]
    
    for pattern, replacement in greek_letters:
        result = result.replace(pattern, replacement)
    
    math_symbols = [
        ('\\times', ' times '),
        ('\\cdot', ' times '),
        ('\\div', ' divided by '),
        ('\\pm', ' plus or minus '),
        ('\\mp', ' minus or plus '),
        ('\\leq', ' less than or equal to '),
        ('\\geq', ' greater than or equal to '),
        ('\\neq', ' not equal to '),
        ('\\approx', ' approximately '),
        ('\\equiv', ' is equivalent to '),
        ('\\infty', ' infinity '),
        ('\\sum', 'sum of '),
        ('\\prod', 'product of '),
        ('\\int', 'integral of '),
        ('\\partial', 'partial '),
        ('\\nabla', 'del '),
        ('\\rightarrow', ' goes to '),
        ('\\leftarrow', ' from '),
        ('\\Rightarrow', ' implies '),
        ('\\therefore', 'therefore '),
        ('\\degree', ' degrees'),
        ('\\circ', ' degrees'),
    ]
    
    for pattern, replacement in math_symbols:
        result = result.replace(pattern, replacement)
    
    # Basic operators
    result = re.sub(r'=', ' equals ', result)
    result = re.sub(r'\+', ' plus ', result)
    # Be careful with minus signs in text, but in latex mode it's okay
    result = re.sub(r'-', ' minus ', result)
    result = re.sub(r'\*', ' times ', result)
    result = re.sub(r'/', ' over ', result)
    result = re.sub(r'<', ' less than ', result)
    result = re.sub(r'>', ' greater than ', result)
    
    # Clean up stray latex commands
    result = re.sub(r'\\[a-zA-Z]+', '', result)
    
    # Remove braces
    result = re.sub(r'[{}]', '', result)
    
    return result.strip()


def _clean_remaining_latex(text: str) -> str:
    """Clean up any remaining LaTeX artifacts that weren't caught."""
    
    text = re.sub(r'\\\[', '', text)
    text = re.sub(r'\\\]', '', text)
    text = re.sub(r'\\begin\{[^}]+\}', '', text)
    text = re.sub(r'\\end\{[^}]+\}', '', text)
    
    # Remove arguments like \textbf{...} but keep content
    text = re.sub(r'\\[a-zA-Z]+\s*\{([^}]*)\}', r'\1', text)
    
    # Remove standalone commands
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    
    text = re.sub(r'[{}]', '', text)
    
    return text
