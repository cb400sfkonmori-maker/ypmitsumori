
# logic.py
# Steel Pole Material Estimation Logic
import math

STEEL_DENSITY_PLATE_FACTOR = 7.85  # kg / (m * m * mm)
PIPE_WEIGHT_FACTOR = 0.02466       # kg / (mm * mm * m) specific factor for pipes
OVERLAP_CORRECTION_M = 0.400       # 400mm overlap correction per connection

def calculate_pipe_weight(diameter_mm: float, thickness_mm: float, length_mm: float, overlap_count: int = 0) -> float:
    """
    Calculate weight of a cylindrical steel pipe (素管).
    Formula: (D - t) * t * 0.02466 * (L(m) + Correction(m))
    """
    try:
        if diameter_mm <= 0 or thickness_mm <= 0 or length_mm <= 0:
            return 0.0
        
        # Convert length to meters
        length_m = length_mm / 1000.0
        
        # Apply Overlap Correction
        total_length_m = length_m + (overlap_count * OVERLAP_CORRECTION_M)
        
        # Calculate Weight
        # (Outer Diameter - Thickness) * Thickness * Factor * Length
        weight = (diameter_mm - thickness_mm) * thickness_mm * PIPE_WEIGHT_FACTOR * total_length_m
        return round(weight, 2)
    except Exception as e:
        print(f"Error calculating pipe weight: {e}")
        return 0.0

def calculate_plate_weight(length_mm: float, width_mm: float, thickness_mm: float, is_rib: bool = False) -> float:
    """
    Calculate weight of a flat steel plate (平板).
    Formula: L(m) * W(m) * t(mm) * 7.85
    If is_rib is True, assumes triangular shape and multiplies by 0.5.
    """
    try:
        if length_mm <= 0 or width_mm <= 0 or thickness_mm <= 0:
            return 0.0
            
        # Convert dimensions to meters
        length_m = length_mm / 1000.0
        width_m = width_mm / 1000.0
        
        weight = length_m * width_m * thickness_mm * STEEL_DENSITY_PLATE_FACTOR
        
        if is_rib:
            weight *= 0.5
            
        return round(weight, 2)
    except Exception as e:
        print(f"Error calculating plate weight: {e}")
        return 0.0

def calculate_surface_area(diameter_mm: float, length_mm: float, width_mm: float = 0, type_str: str = "pipe", overlap_count: int = 0, is_rib: bool = False) -> float:
    """
    Calculate Surface Area (Painting Area).
    For Pipes: S = pi * D(m) * L(m)
    For Plates: S = 2 * (L(m) * W(m)) 
    If is_rib is True (Triangle): S approx L(m) * W(m) (2 sides)
    """
    try:
        length_m = length_mm / 1000.0
        
        if "pipe" in type_str.lower():
            if diameter_mm <= 0: return 0.0
            total_length_m = length_m + (overlap_count * OVERLAP_CORRECTION_M)
            diameter_m = diameter_mm / 1000.0
            # S = pi * D * L
            area = math.pi * diameter_m * total_length_m
            return round(area, 3)
        
        elif "plate" in type_str.lower():
            # For plates, usually painting area is surface area (2 sides) + edges
            width_m = width_mm / 1000.0
            area = 2 * (length_m * width_m)
            
            if is_rib:
                area *= 0.5
                
            return round(area, 3)
            
        return 0.0
    except Exception:
        return 0.0
