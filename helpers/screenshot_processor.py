"""Screenshot processing and OCR for stat extraction"""
import io
import re
from typing import Dict, Optional, Tuple

# Optional imports for OCR functionality
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: pytesseract or Pillow not installed. Screenshot processing will be disabled.")

# Configure tesseract path if needed (uncomment and set if tesseract is not in PATH)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy
    """
    # Convert to grayscale for better OCR
    if image.mode != 'L':
        image = image.convert('L')
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)
    
    # Scale up if image is too small (OCR works better on larger images)
    width, height = image.size
    if width < 800 or height < 600:
        scale_factor = max(800 / width, 600 / height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Apply slight denoising
    image = image.filter(ImageFilter.MedianFilter(size=3))
    
    return image


def parse_number_with_commas(text: str) -> Optional[int]:
    """
    Parse a number that may contain commas (e.g., "1,234,567")
    """
    # Remove commas and try to parse
    cleaned = text.replace(',', '').strip()
    try:
        return int(cleaned)
    except ValueError:
        return None


def extract_stats_from_image(image_bytes: bytes) -> Tuple[Optional[Dict[str, int]], Optional[str]]:
    """
    Extract Foxhole stats from a screenshot using OCR
    Returns a tuple of (stats dictionary, error_message)
    - stats: Dictionary with stat values or None if extraction fails
    - error_message: Error message for debugging or None if successful
    """
    if not OCR_AVAILABLE:
        return None, "OCR libraries not available. Please install pytesseract and Pillow."
    
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Preprocess image for better OCR
        processed_image = preprocess_image(image)
        
        # Perform OCR with custom config for better number recognition
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789,ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz:()[]- '
        text = pytesseract.image_to_string(processed_image, config=custom_config)
        
        # Also try without custom config as fallback
        if not text or len(text.strip()) < 10:
            text = pytesseract.image_to_string(processed_image)
        
        # Debug: print extracted text (first 500 chars)
        print(f"OCR extracted text (first 500 chars): {text[:500]}")
        
        if not text or len(text.strip()) < 10:
            return None, "Could not extract readable text from image. The image may be too blurry or contain no text."
        
        # Parse the text for stats
        stats = {}
        
        # More flexible patterns that handle various formats
        # Patterns now handle:
        # - Different spacing
        # - Optional colons
        # - Numbers with or without commas
        # - Case variations
        patterns = {
            'enemy_player_damage': [
                r'enemy\s*player\s*damage\s*:?\s*([\d,]+)',
                r'enemy\s*player\s*damage\s*:?\s*(\d{1,3}(?:,\d{3})*)',
                r'enemy.*?player.*?damage\s*:?\s*([\d,]+)',
            ],
            'friendly_player_damage': [
                r'friendly\s*player\s*damage\s*:?\s*([\d,]+)',
                r'friendly\s*player\s*damage\s*:?\s*(\d{1,3}(?:,\d{3})*)',
                r'friendly.*?player.*?damage\s*:?\s*([\d,]+)',
            ],
            'enemy_structure_vehicle_damage': [
                r'enemy\s*(?:structure|vehicle)\s*damage\s*:?\s*([\d,]+)',
                r'enemy.*?(?:structure|vehicle).*?damage\s*:?\s*([\d,]+)',
            ],
            'friendly_structure_vehicle_damage': [
                r'friendly\s*(?:structure|vehicle)\s*damage\s*:?\s*([\d,]+)',
                r'friendly.*?(?:structure|vehicle).*?damage\s*:?\s*([\d,]+)',
            ],
            'friendly_construction': [
                r'friendly\s*construction\s*:?\s*([\d,]+)',
                r'friendly.*?construction\s*:?\s*([\d,]+)',
            ],
            'friendly_repairing': [
                r'friendly\s*repairing\s*:?\s*([\d,]+)',
                r'friendly.*?repairing\s*:?\s*([\d,]+)',
            ],
            'friendly_healing': [
                r'friendly\s*healing\s*:?\s*([\d,]+)',
                r'friendly.*?healing\s*:?\s*([\d,]+)',
            ],
            'friendly_revivals': [
                r'friendly\s*revivals?\s*:?\s*([\d,]+)',
                r'friendly.*?revivals?\s*:?\s*([\d,]+)',
            ],
            'vehicles_captured_by_enemy': [
                r'vehicles?\s*captured\s*by\s*enemy\s*:?\s*([\d,]+)',
                r'vehicles?.*?captured.*?enemy\s*:?\s*([\d,]+)',
            ],
            'vehicle_self_damage_neutral': [
                r'vehicle\s*self\s*damage\s*\(?\s*neutral\s*\)?\s*:?\s*([\d,]+)',
                r'vehicle.*?self.*?damage.*?neutral\s*:?\s*([\d,]+)',
            ],
            'vehicle_self_damage_colonial': [
                r'vehicle\s*self\s*damage\s*\(?\s*colonial\s*\)?\s*:?\s*([\d,]+)',
                r'vehicle.*?self.*?damage.*?colonial\s*:?\s*([\d,]+)',
            ],
            'vehicle_self_damage_warden': [
                r'vehicle\s*self\s*damage\s*\(?\s*warden\s*\)?\s*:?\s*([\d,]+)',
                r'vehicle.*?self.*?damage.*?warden\s*:?\s*([\d,]+)',
            ],
            'materials_submitted': [
                r'materials?\s*submitted\s*:?\s*([\d,]+)',
                r'materials?.*?submitted\s*:?\s*([\d,]+)',
            ],
            'materials_gathered': [
                r'materials?\s*gathered\s*:?\s*([\d,]+)',
                r'materials?.*?gathered\s*:?\s*([\d,]+)',
            ],
            'supply_value_delivered': [
                r'supply\s*value\s*delivered\s*:?\s*([\d,]+)',
                r'supply.*?value.*?delivered\s*:?\s*([\d,]+)',
            ],
        }
        
        # Try to find each stat using multiple patterns
        for stat_name, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        number_text = match.group(1)
                        value = parse_number_with_commas(number_text)
                        if value is not None:
                            stats[stat_name] = value
                            break  # Found a match, move to next stat
                    except (ValueError, IndexError):
                        continue
        
        # Fallback: If we didn't find many stats, try a more aggressive approach
        # Look for numbers near keywords even if format doesn't match exactly
        if len(stats) < 5:
            # Keywords for each stat (simplified)
            keyword_map = {
                'enemy_player_damage': ['enemy', 'player', 'damage'],
                'friendly_player_damage': ['friendly', 'player', 'damage'],
                'enemy_structure_vehicle_damage': ['enemy', 'structure', 'vehicle', 'damage'],
                'friendly_structure_vehicle_damage': ['friendly', 'structure', 'vehicle', 'damage'],
                'friendly_construction': ['friendly', 'construction'],
                'friendly_repairing': ['friendly', 'repairing'],
                'friendly_healing': ['friendly', 'healing'],
                'friendly_revivals': ['friendly', 'revival'],
                'vehicles_captured_by_enemy': ['vehicle', 'captured', 'enemy'],
                'vehicle_self_damage_neutral': ['vehicle', 'self', 'damage', 'neutral'],
                'vehicle_self_damage_colonial': ['vehicle', 'self', 'damage', 'colonial'],
                'vehicle_self_damage_warden': ['vehicle', 'self', 'damage', 'warden'],
                'materials_submitted': ['material', 'submitted'],
                'materials_gathered': ['material', 'gathered'],
                'supply_value_delivered': ['supply', 'value', 'delivered'],
            }
            
            # Split text into lines for line-by-line analysis
            lines = text.split('\n')
            
            for stat_name, keywords in keyword_map.items():
                if stat_name in stats:
                    continue  # Already found
                
                # Look for lines containing the keywords
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    # Check if line contains most keywords
                    keyword_matches = sum(1 for kw in keywords if kw in line_lower)
                    if keyword_matches >= len(keywords) - 1:  # Allow one keyword to be missing
                        # Look for numbers in this line or nearby lines
                        for check_line in lines[max(0, i-1):i+2]:  # Check current line and adjacent lines
                            # Find all numbers in the line
                            numbers = re.findall(r'[\d,]+', check_line)
                            for num_str in numbers:
                                value = parse_number_with_commas(num_str)
                                if value is not None and value >= 0 and value <= 999999999:
                                    stats[stat_name] = value
                                    break
                        if stat_name in stats:
                            break
        
        if not stats:
            # Return the extracted text for debugging
            preview_text = text[:500].replace('\n', ' ').strip()
            return None, f"No stats found in extracted text. Extracted text preview: {preview_text}..."
        
        return stats, None
        
    except Exception as e:
        error_msg = f"Error processing screenshot: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return None, error_msg


def validate_stats(stats: Dict[str, int]) -> bool:
    """Validate that stats are reasonable"""
    # Check for negative values
    if any(v < 0 for v in stats.values()):
        return False
    
    # Check for unreasonably large values (matches data governance rules)
    max_value = 999999999
    if any(v > max_value for v in stats.values()):
        return False
    
    return True

