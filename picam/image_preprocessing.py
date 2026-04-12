"""
Image Preprocessing Pipeline for RoboCapture
Implements the two-stage filtering and feature extraction for intelligent image transmission
"""

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import json

# ============================================================================
# STAGE 0: IMAGE CAPTURE AND RESIZING
# ============================================================================

class ImageCaptureProcessor:
    """Handles image capture and resizing for analysis"""
    
    def __init__(self, original_size=(1080, 1920), analysis_size=(224, 224)):
        self.original_size = original_size
        self.analysis_size = analysis_size
    
    def prepare_images(self, image_path):
        """Load image and create two copies"""
        original_img = cv2.imread(image_path)
        if original_img is None:
            raise ValueError(f"Cannot read image from {image_path}")
        
        resized_img = cv2.resize(original_img, self.analysis_size)
        return original_img, resized_img


# ============================================================================
# STAGE 0.5: CHANGE DETECTION
# ============================================================================

class ChangeDetector:
    """Detects significant changes between consecutive frames"""
    
    def __init__(self, difference_threshold=5.0):
        self.difference_threshold = difference_threshold
        self.previous_frame = None
    
    def detect_change(self, current_frame, explicit_previous_frame=None):
        """Compare current frame with previous frame (either internal state or explicit)"""
        # Prioritize explicitly passed frame, fallback to internal state
        prev_frame_to_use = explicit_previous_frame if explicit_previous_frame is not None else self.previous_frame

        if prev_frame_to_use is None:
            self.previous_frame = current_frame.copy()
            return True, 100.0
        
        gray_current = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        gray_previous = cv2.cvtColor(prev_frame_to_use, cv2.COLOR_BGR2GRAY)
        
        frame_diff = cv2.absdiff(gray_current, gray_previous)
        
        threshold = 30
        changed_pixels = np.sum(frame_diff > threshold)
        total_pixels = frame_diff.size
        change_percentage = (changed_pixels / total_pixels) * 100
        
        # Always update internal state for the next potential call
        self.previous_frame = current_frame.copy()
        
        has_change = change_percentage > self.difference_threshold
        
        return has_change, change_percentage



# ============================================================================
# STAGE 1: LOW-LEVEL IMAGE FILTERING
# ============================================================================

class LowLevelImageFilter:
    """Stage 1: Extract low-level image quality features"""
    
    def __init__(self, brightness_min=40, brightness_max=255, 
                 blur_threshold=100, edge_threshold=50):
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max
        self.blur_threshold = blur_threshold
        self.edge_threshold = edge_threshold
    
    def convert_to_grayscale(self, image):
        """Convert BGR image to grayscale"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return gray
    
    def compute_brightness(self, gray_image):
        """Compute average brightness"""
        brightness = np.mean(gray_image)
        return brightness
    
    def compute_saturation(self, image):
        """Compute average saturation"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation = np.mean(hsv[:, :, 1])
        return saturation
    
    def detect_edges(self, gray_image):
        """Detect edges using Canny"""
        edges = cv2.Canny(gray_image, 100, 200)
        edge_count = np.sum(edges > 0)
        return edges, edge_count
    
    def compute_sharpness(self, gray_image):
        """Measure image sharpness using Laplacian variance"""
        laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
        sharpness = np.var(laplacian)
        return sharpness
    
    def apply_gaussian_blur_analysis(self, image):
        """Apply Gaussian blur for analysis"""
        blurred = cv2.GaussianBlur(image, (5, 5), 0)
        return blurred
    
    def compute_fft_features(self, gray_image):
        """Compute FFT to analyze frequency/detail information"""
        f_transform = np.fft.fft2(gray_image)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.abs(f_shift)
        mean_frequency = np.mean(magnitude_spectrum)
        return magnitude_spectrum, mean_frequency
    
    def apply_filters(self, image, verbose=True):
        """Apply all low-level filters"""
        results = {}
        passes = True
        
        gray = self.convert_to_grayscale(image)
        results['grayscale'] = gray
        
        brightness = self.compute_brightness(gray)
        results['brightness'] = brightness
        brightness_ok = self.brightness_min <= brightness <= self.brightness_max
        results['brightness_check'] = brightness_ok
        if not brightness_ok:
            passes = False
            if verbose:
                print(f"❌ Brightness check FAILED: {brightness:.2f} (range: {self.brightness_min}-{self.brightness_max})")
        else:
            if verbose:
                print(f"✓ Brightness check PASSED: {brightness:.2f}")
        
        saturation = self.compute_saturation(image)
        results['saturation'] = saturation
        if verbose:
            print(f"  Saturation: {saturation:.2f}")
        
        blurred = self.apply_gaussian_blur_analysis(image)
        results['blurred'] = blurred
        
        edges, edge_count = self.detect_edges(gray)
        results['edges'] = edges
        results['edge_count'] = edge_count
        if verbose:
            print(f"  Edge count: {edge_count}")
        
        sharpness = self.compute_sharpness(gray)
        results['sharpness'] = sharpness
        sharpness_ok = sharpness > self.blur_threshold
        results['sharpness_check'] = sharpness_ok
        if not sharpness_ok:
            passes = False
            if verbose:
                print(f"❌ Sharpness check FAILED: {sharpness:.2f} (threshold: {self.blur_threshold})")
        else:
            if verbose:
                print(f"✓ Sharpness check PASSED: {sharpness:.2f}")
        
        magnitude_spectrum, mean_frequency = self.compute_fft_features(gray)
        results['fft_magnitude'] = magnitude_spectrum
        results['mean_frequency'] = mean_frequency
        if verbose:
            print(f"  Mean frequency (detail): {mean_frequency:.2f}")
        
        return passes, results


# ============================================================================
# STAGE 2: SEMANTIC FEATURE EXTRACTION
# ============================================================================

class SemanticFeatureExtractor:
    """Stage 2: Extract semantic features using MobileNetV2"""
    
    def __init__(self, model_name='mobilenet_v2', embedding_size=1280):
        self.model_name = model_name
        self.embedding_size = embedding_size
        
        self.model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
        self.model.eval()
        
        self.model.classifier = torch.nn.Identity()

        #removed setgrad false        
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], 
                                [0.229, 0.224, 0.225])
        ])
    
    def extract_embedding(self, image_cv2):
        """Extract semantic embedding from image"""
        image_rgb = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(image_rgb)
        
        tensor = self.transform(image_pil).unsqueeze(0)
        
        with torch.no_grad():
            embedding = self.model(tensor)
        
        embedding = embedding.squeeze().numpy()
        
        return embedding
    
    def extract_features(self, image, verbose=True):
        """Extract semantic features and return results"""
        results = {}
        
        try:
            embedding = self.extract_embedding(image)
            results['embedding'] = embedding
            results['embedding_shape'] = embedding.shape
            results['embedding_magnitude'] = np.linalg.norm(embedding)
            
            if verbose:
                print(f"✓ Embedding extracted: shape {embedding.shape}, magnitude {results['embedding_magnitude']:.4f}")
            
            return True, results
        
        except Exception as e:
            print(f"❌ Embedding extraction FAILED: {e}")
            return False, {}


# ============================================================================
# MAIN PREPROCESSING PIPELINE
# ============================================================================

class ImagePreprocessingPipeline:
    """Complete preprocessing pipeline"""
    
    def __init__(self, 
                 original_size=(1080, 1920),
                 analysis_size=(224, 224),
                 brightness_min=40,
                 brightness_max=255,
                 blur_threshold=100,
                 change_threshold=5.0):
        
        self.capture_processor = ImageCaptureProcessor(original_size, analysis_size)
        self.change_detector = ChangeDetector(change_threshold)
        self.low_level_filter = LowLevelImageFilter(
            brightness_min=brightness_min,
            brightness_max=brightness_max,
            blur_threshold=blur_threshold
        )
        self.semantic_extractor = SemanticFeatureExtractor()
    
    def process_image(self, current_image_path, previous_image_path=None, verbose=True):
        """Complete preprocessing pipeline for a single image"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'current_image_path': str(current_image_path),
            'previous_image_path': str(previous_image_path) if previous_image_path else None,
            'stage_0': {},
            'stage_0_5': {},
            'stage_1': {},
            'stage_2': {},
            'final_decision': False
        }
        
        try:
            # STAGE 0: Capture and Resize
            if verbose:
                print("\n" + "="*70)
                print("STAGE 0: IMAGE CAPTURE AND RESIZING")
                print("="*70)
            
            original_img, resized_img = self.capture_processor.prepare_images(current_image_path)
            results['stage_0']['original_shape'] = original_img.shape
            results['stage_0']['resized_shape'] = resized_img.shape
            
            if verbose:
                print(f"✓ Current image: {original_img.shape} -> {resized_img.shape}")
            
            # Prepare explicit previous image if provided
            previous_resized_img = None
            if previous_image_path is not None:
                _, previous_resized_img = self.capture_processor.prepare_images(previous_image_path)
                if verbose:
                    print(f"✓ Explicit previous image loaded: {previous_image_path}")

            # STAGE 0.5: Change Detection
            if verbose:
                print("\n" + "="*70)
                print("STAGE 0.5: CHANGE DETECTION")
                print("="*70)
            
            has_change, change_pct = self.change_detector.detect_change(
                resized_img, 
                explicit_previous_frame=previous_resized_img
            )
            
            results['stage_0_5']['has_significant_change'] = has_change
            results['stage_0_5']['change_percentage'] = change_pct
            
            if verbose:
                print(f"Change detected: {change_pct:.2f}%")
                if has_change:
                    print("✓ Significant change detected - continuing to Stage 1")
                else:
                    print("❌ No significant change - image discarded")
            
            if not has_change:
                results['final_decision'] = False
                return False, results
            
            # STAGE 1: Low-Level Image Filtering
            if verbose:
                print("\n" + "="*70)
                print("STAGE 1: LOW-LEVEL IMAGE FILTERING")
                print("="*70)
            
            stage1_passes, stage1_results = self.low_level_filter.apply_filters(resized_img, verbose=verbose)
            results['stage_1'] = {
                'passes': stage1_passes,
                'brightness': stage1_results['brightness'],
                'brightness_check': stage1_results['brightness_check'],
                'saturation': stage1_results['saturation'],
                'sharpness': stage1_results['sharpness'],
                'sharpness_check': stage1_results['sharpness_check'],
                'edge_count': stage1_results['edge_count'],
                'mean_frequency': stage1_results['mean_frequency']
            }
            
            if not stage1_passes:
                if verbose:
                    print("\n❌ Stage 1 FAILED - Image rejected")
                results['final_decision'] = False
                return False, results
            
            if verbose:
                print("\n✓ Stage 1 PASSED - Continuing to Stage 2")
            
            # STAGE 2: Semantic Feature Extraction
            if verbose:
                print("\n" + "="*70)
                print("STAGE 2: SEMANTIC FEATURE EXTRACTION")
                print("="*70)
            
            stage2_passes, stage2_results = self.semantic_extractor.extract_features(resized_img, verbose=verbose)
            results['stage_2'] = {
                'passes': stage2_passes,
                'embedding_shape': list(stage2_results.get('embedding_shape', [])),
                'embedding_magnitude': float(stage2_results.get('embedding_magnitude', 0))
            }
            
            if not stage2_passes:
                if verbose:
                    print("\n❌ Stage 2 FAILED - Image rejected")
                results['final_decision'] = False
                return False, results
            
            # FINAL DECISION
            if verbose:
                print("\n" + "="*70)
                print("FINAL DECISION")
                print("="*70)
                print("✓✓✓ IMAGE PASSES ALL FILTERS - READY FOR TRANSMISSION ✓✓✓")
                print("="*70)
            
            results['final_decision'] = True
            results['embedding'] = stage2_results['embedding'].tolist()
            
            return True, results
        
        except Exception as e:
            if verbose:
                print(f"\n❌ PIPELINE ERROR: {e}")
            results['error'] = str(e)
            results['final_decision'] = False
            return False, results