"""
Real-Time Multi-Angle Posture Detection System using MediaPipe

Installation Instructions:
1. Ensure you have Python 3.10+ installed.
2. Install the required dependencies:
   pip install opencv-python mediapipe numpy

Usage:
   python posture_detector.py
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import math

# ==============================================================================
# THRESHOLDS & CONSTANTS
# ==============================================================================

# Visiblity
VISIBILITY_THRESHOLD = 0.5

# Position Classification
SITTING_KNEE_BEND_MAX = 140       # If knee is bent more than 140 deg, sitting (Side/Front approximated)
SLEEPING_TORSO_HORIZONTAL_MAX_ANGLE = 45 # If torso angle from horizontal is small, sleeping

# Neck Posture
NECK_TILT_THRESH = 10         # degrees for Left/Right Tilt
NECK_BEND_Z_THRESH = 0.08     # z-axis depth difference between ear and shoulder (Front/Back)
NECK_FWD_BEND_SIDE_THRESH = 15# Forward neck lean vs vertical (Side View)

# Shoulder Posture
SHOULDER_DROP_THRESH = 0.03   # Normalized y difference between left and right shoulders
SHOULDER_ASYM_THRESH = 0.05   # Uneven shoulder height

# Spine Posture
SPINE_CURVE_THRESH = 10       # Left/Right Curve deviation from vertical
SPINE_SLOUCH_THRESH = 15      # Forward slough from vertical (Side View)
SPINE_ARCH_THRESH = -10       # Excessive back arch (Side View)

# Knee Posture
KNEE_VALGUS_VARUS_DIST = 0.05
KNEE_UNEVEN_Y_THRESH = 0.05
KNEE_OVERBENT_THRESH = 60     # Angle < 60 is over-bent
KNEE_HYPEREXTENDED_THRESH = 175 # Angle > 175 is hyperextended

# ==============================================================================

class PostureDetector:
    def __init__(self):
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        
        # Mapping constants for convenience
        self.LM = self.mp_pose.PoseLandmark

        # State Variables
        self.current_mode = "UPPER_BODY"
        self.current_view = "FRONT"
        self.current_position = "STANDING"
        
        # Track previous time for FPS
        self.pTime = 0

    def calculate_angle(self, pointA, pointB, pointC):
        """
        Calculate the angle between three points (in 2D space, usually x and y).
        pointA, pointB, pointC are tuples or lists (x, y).
        pointB is the vertex.
        Returns angle in degrees.
        """
        if not (pointA and pointB and pointC):
            return 0.0
            
        a = np.array(pointA)
        b = np.array(pointB)
        c = np.array(pointC)

        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)

        if angle > 180.0:
            angle = 360 - angle

        return angle

    def calculate_slope_angle_vertical(self, p1, p2):
        """ Angle of the line connecting p1 and p2 with the vertical axis """
        if not (p1 and p2): return 0.0
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        if dy == 0: return 90.0
        return math.degrees(math.atan(dx / dy)) # sign gives direction

    def calculate_slope_angle_horizontal(self, p1, p2):
        """ Angle of the line connecting p1 and p2 with the horizontal axis """
        if not (p1 and p2): return 0.0
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        if dx == 0: return 90.0
        return math.degrees(math.atan(dy / dx)) # sign gives direction

    def get_point(self, landmarks, point_enum):
        """ Helper to get x, y, z coordinates if visibility is high enough """
        if not landmarks: return None
        landmark = landmarks.landmark[point_enum]
        if landmark.visibility < VISIBILITY_THRESHOLD:
            return None
        return [landmark.x, landmark.y, landmark.z]
    
    def mid_point(self, p1, p2):
        if not p1 or not p2: return None
        return [(p1[0]+p2[0])/2, (p1[1]+p2[1])/2, (p1[2]+p2[2])/2]

    def detect_mode(self, coords):
        """ Determine if FULL_BODY or UPPER_BODY is visible """
        upper_visible = coords['l_shoulder'] and coords['r_shoulder'] and coords['l_hip'] and coords['r_hip']
        lower_visible = coords['l_knee'] and coords['r_knee'] and coords['l_ankle'] and coords['r_ankle']
        
        if upper_visible and lower_visible:
            return "FULL_BODY"
        elif upper_visible:
            return "UPPER_BODY"
        return "UNKNOWN"

    def detect_view(self, coords):
        """
        Detect View: Front, Back, Left Side, Right Side
        Uses shoulder depth differences and nose position.
        """
        l_sh = coords['l_shoulder']
        r_sh = coords['r_shoulder']
        nose = coords['nose']
        
        if l_sh and r_sh:
            z_diff = abs(l_sh[2] - r_sh[2])
            x_diff = abs(l_sh[0] - r_sh[0])
            
            # If Z difference is significant compared to X difference, it's a side profile
            if z_diff > x_diff * 1.2:
                # Closer shoulder has a smaller (more negative) z value
                if l_sh[2] < r_sh[2]:
                    return "LEFT_SIDE"
                else:
                    return "RIGHT_SIDE"
                    
            # Differentiate Front and Back
            if nose:
                # If nose is closer (smaller z) than shoulders mid-z, it's front
                mid_sh_z = (l_sh[2] + r_sh[2]) / 2
                if nose[2] < mid_sh_z:
                    return "FRONT"
                else:
                    return "BACK"
        return "UNKNOWN"

    def detect_position(self, coords, view):
        """
        Detect Position: Standing, Sitting, Sleeping
        Based on torso orientation vs gravity and knee angles.
        """
        l_sh = coords['l_shoulder']
        l_hip = coords['l_hip']
        l_knee = coords['l_knee']
        l_ankle = coords['l_ankle']
        
        r_sh = coords['r_shoulder']
        r_hip = coords['r_hip']
        r_knee = coords['r_knee']
        r_ankle = coords['r_ankle']
        
        mid_sh = self.mid_point(l_sh, r_sh)
        mid_hip = self.mid_point(l_hip, r_hip)
        
        if mid_sh and mid_hip:
            # Check for Sleeping (torso is mostly horizontal)
            torso_angle_h = abs(self.calculate_slope_angle_horizontal(mid_sh, mid_hip))
            if torso_angle_h < SLEEPING_TORSO_HORIZONTAL_MAX_ANGLE:
                return "SLEEPING"
                
            # Check for Sitting vs Standing (using knee angle)
            # If knees aren't fully visible, we assume standing if Torso is vertical
            if l_hip and l_knee and l_ankle:
                l_k_angle = self.calculate_angle(l_hip, l_knee, l_ankle)
                if l_k_angle < SITTING_KNEE_BEND_MAX:
                    return "SITTING"
            elif r_hip and r_knee and r_ankle:
                r_k_angle = self.calculate_angle(r_hip, r_knee, r_ankle)
                if r_k_angle < SITTING_KNEE_BEND_MAX:
                    return "SITTING"
                    
        return "STANDING"

    def detect_upper_body_posture(self, coords, issues, problematic_joints):
        """
        Upper Body Routine (Neck, Shoulders, Spine)
        """
        view = self.current_view
        
        l_ear = coords['l_ear']
        r_ear = coords['r_ear']
        nose = coords['nose']
        l_sh = coords['l_shoulder']
        r_sh = coords['r_shoulder']
        l_hip = coords['l_hip']
        r_hip = coords['r_hip']
        
        mid_sh = self.mid_point(l_sh, r_sh)
        mid_hip = self.mid_point(l_hip, r_hip)
        
        # --- A) NECK POSTURE ---
        if view in ["FRONT", "BACK"]:
            # Neck Tilt (Left / Right)
            if mid_sh and nose:
                neck_angle_v = self.calculate_slope_angle_vertical(nose, mid_sh)
                if neck_angle_v < -NECK_TILT_THRESH:
                    issues.append(f"Neck Right Tilt ({int(abs(neck_angle_v))}°)")
                    problematic_joints.update(['nose', 'l_shoulder', 'r_shoulder'])
                elif neck_angle_v > NECK_TILT_THRESH:
                    issues.append(f"Neck Left Tilt ({int(abs(neck_angle_v))}°)")
                    problematic_joints.update(['nose', 'l_shoulder', 'r_shoulder'])

            # Neck Forward / Backward Bend (Estimated via Z depth difference between Ear and Shoulder)
            if (l_ear and r_ear) and mid_sh:
                mid_ear_z = (l_ear[2] + r_ear[2]) / 2.0
                z_diff = mid_ear_z - mid_sh[2]
                
                # In front view, smaller z means closer to camera
                if view == "FRONT":
                    if z_diff < -NECK_BEND_Z_THRESH:
                        issues.append("Neck Forward Bend")
                        problematic_joints.update(['l_ear', 'r_ear', 'l_shoulder', 'r_shoulder'])
                    elif z_diff > NECK_BEND_Z_THRESH:
                        issues.append("Neck Backward Bend")
                        problematic_joints.update(['l_ear', 'r_ear', 'l_shoulder', 'r_shoulder'])
                else: # BACK view (closer to camera means backward bend)
                    if z_diff < -NECK_BEND_Z_THRESH:
                        issues.append("Neck Backward Bend")
                        problematic_joints.update(['l_ear', 'r_ear', 'l_shoulder', 'r_shoulder'])
                    elif z_diff > NECK_BEND_Z_THRESH:
                        issues.append("Neck Forward Bend")
                        problematic_joints.update(['l_ear', 'r_ear', 'l_shoulder', 'r_shoulder'])
                    
        elif view in ["LEFT_SIDE", "RIGHT_SIDE"]:
            ear = l_ear if view == "LEFT_SIDE" else r_ear
            sh = l_sh if view == "LEFT_SIDE" else r_sh
            
            # Forward / Backward Bend
            if ear and sh:
                neck_fwd_angle = self.calculate_slope_angle_vertical(ear, sh)
                if view == "LEFT_SIDE":
                    if neck_fwd_angle > NECK_FWD_BEND_SIDE_THRESH:
                        issues.append(f"Neck Forward Bend ({int(neck_fwd_angle)}°)")
                        problematic_joints.update(['l_ear', 'l_shoulder'])
                    elif neck_fwd_angle < -NECK_FWD_BEND_SIDE_THRESH:
                        issues.append(f"Neck Backward Bend ({int(abs(neck_fwd_angle))}°)")
                        problematic_joints.update(['l_ear', 'l_shoulder'])
                else: # RIGHT_SIDE (flipped horizontal)
                    if neck_fwd_angle < -NECK_FWD_BEND_SIDE_THRESH:
                        issues.append(f"Neck Forward Bend ({int(abs(neck_fwd_angle))}°)")
                        problematic_joints.update(['r_ear', 'r_shoulder'])
                    elif neck_fwd_angle > NECK_FWD_BEND_SIDE_THRESH:
                        issues.append(f"Neck Backward Bend ({int(neck_fwd_angle)}°)")
                        problematic_joints.update(['r_ear', 'r_shoulder'])

        # --- B) SHOULDER POSTURE ---
        if view in ["FRONT", "BACK"]:
            if l_sh and r_sh:
                y_diff = l_sh[1] - r_sh[1] # Negative if left is higher
                # Left / Right Shoulder Drop
                if y_diff > SHOULDER_DROP_THRESH:
                    issues.append("Left Shoulder Drop")
                    problematic_joints.update(['l_shoulder', 'r_shoulder'])
                elif y_diff < -SHOULDER_DROP_THRESH:
                    issues.append("Right Shoulder Drop")
                    problematic_joints.update(['l_shoulder', 'r_shoulder'])
                elif abs(y_diff) > SHOULDER_ASYM_THRESH:
                    issues.append("Uneven Shoulder Height")
                    problematic_joints.update(['l_shoulder', 'r_shoulder'])

        # --- C) SPINE POSTURE ---
        if view in ["FRONT", "BACK"]:
            # Spine Curve
            if mid_sh and mid_hip:
                spine_angle_v = self.calculate_slope_angle_vertical(mid_sh, mid_hip)
                if spine_angle_v > SPINE_CURVE_THRESH:
                    issues.append(f"Spine Left Curve ({int(spine_angle_v)}°)")
                    problematic_joints.update(['l_shoulder', 'r_shoulder', 'l_hip', 'r_hip'])
                elif spine_angle_v < -SPINE_CURVE_THRESH:
                    issues.append(f"Spine Right Curve ({int(abs(spine_angle_v))}°)")
                    problematic_joints.update(['l_shoulder', 'r_shoulder', 'l_hip', 'r_hip'])
                    
        elif view in ["LEFT_SIDE", "RIGHT_SIDE"]:
            if mid_sh and mid_hip:
                spine_angle_v = self.calculate_slope_angle_vertical(mid_sh, mid_hip)
                if view == "LEFT_SIDE":
                    if spine_angle_v > SPINE_SLOUCH_THRESH:
                        issues.append(f"Slouched Forward ({int(spine_angle_v)}°)")
                        problematic_joints.update(['l_shoulder', 'r_shoulder', 'l_hip', 'r_hip'])
                    elif spine_angle_v < SPINE_ARCH_THRESH:
                        issues.append(f"Excessive Back Arch ({int(abs(spine_angle_v))}°)")
                        problematic_joints.update(['l_shoulder', 'r_shoulder', 'l_hip', 'r_hip'])
                else: # RIGHT_SIDE
                    if spine_angle_v < -SPINE_SLOUCH_THRESH:
                        issues.append(f"Slouched Forward ({int(abs(spine_angle_v))}°)")
                        problematic_joints.update(['l_shoulder', 'r_shoulder', 'l_hip', 'r_hip'])
                    elif spine_angle_v > -SPINE_ARCH_THRESH:
                        issues.append(f"Excessive Back Arch ({int(spine_angle_v)}°)")
                        problematic_joints.update(['l_shoulder', 'r_shoulder', 'l_hip', 'r_hip'])


    def detect_full_body_posture(self, coords, issues, problematic_joints):
        """
        Full Body Routine (Knees, Legs)
        Runs after Upper Body routine.
        """
        view = self.current_view
        
        l_hip = coords['l_hip']
        r_hip = coords['r_hip']
        l_knee = coords['l_knee']
        r_knee = coords['r_knee']
        l_ankle = coords['l_ankle']
        r_ankle = coords['r_ankle']
        
        # --- D) KNEE POSTURE ---
        if view in ["FRONT", "BACK"]:
            # Uneven Knee Height
            if l_knee and r_knee:
                y_diff = l_knee[1] - r_knee[1]
                if abs(y_diff) > KNEE_UNEVEN_Y_THRESH:
                    issues.append("Uneven Knee Height")
                    problematic_joints.update(['l_knee', 'r_knee'])
                    
            # Knee Valgus / Varus
            if l_knee and r_knee and l_ankle and r_ankle:
                dist_knees = abs(l_knee[0] - r_knee[0])
                dist_ankles = abs(l_ankle[0] - r_ankle[0])
                if dist_knees < dist_ankles - KNEE_VALGUS_VARUS_DIST:
                    issues.append("Knee Valgus (Inward)")
                    problematic_joints.update(['l_knee', 'r_knee'])
                elif dist_knees > dist_ankles + KNEE_VALGUS_VARUS_DIST:
                    issues.append("Knee Varus (Outward)")
                    problematic_joints.update(['l_knee', 'r_knee'])

            # Asymmetry
            if view == "BACK":
                if l_knee and r_knee and l_hip and r_hip:
                    l_angle = self.calculate_slope_angle_vertical(l_hip, l_knee)
                    r_angle = self.calculate_slope_angle_vertical(r_hip, r_knee)
                    if abs(l_angle - r_angle) > 15: # 15 degree diff
                        issues.append("Leg Misalignment / Asymmetry")
                        problematic_joints.update(['l_hip', 'r_hip', 'l_knee', 'r_knee'])

        elif view in ["LEFT_SIDE", "RIGHT_SIDE"]:
            # Over-bent vs Hyperextended
            for side in [('l_hip', 'l_knee', 'l_ankle'), ('r_hip', 'r_knee', 'r_ankle')]:
                hip = coords[side[0]]
                knee = coords[side[1]]
                ankle = coords[side[2]]
                
                if hip and knee and ankle:
                    angle = self.calculate_angle(hip, knee, ankle)
                    is_left = 'l_' in side[0]
                    prefix = "Left" if is_left else "Right"
                    
                    if angle > KNEE_HYPEREXTENDED_THRESH:
                        issues.append(f"{prefix} Hyperextended Knee ({int(angle)}°)")
                        problematic_joints.update([side[0], side[1], side[2]])
                    elif angle < KNEE_OVERBENT_THRESH and self.current_position != "SITTING":
                        # Only flag over-bent if standing
                        issues.append(f"{prefix} Over-bent Knee ({int(angle)}°)")
                        problematic_joints.update([side[0], side[1], side[2]])

    def process_frame(self, frame):
        # Convert BGR to RGB
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        
        # Make detection
        results = self.pose.process(image)
        
        # Recolor back to BGR
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        issues = []
        problematic_joints = set()
        correct_joints = set()
        coords = {}
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks
            
            # Extract key coordinates safely
            mapping = {
                'nose': self.LM.NOSE,
                'l_ear': self.LM.LEFT_EAR,
                'r_ear': self.LM.RIGHT_EAR,
                'l_shoulder': self.LM.LEFT_SHOULDER,
                'r_shoulder': self.LM.RIGHT_SHOULDER,
                'l_hip': self.LM.LEFT_HIP,
                'r_hip': self.LM.RIGHT_HIP,
                'l_knee': self.LM.LEFT_KNEE,
                'r_knee': self.LM.RIGHT_KNEE,
                'l_ankle': self.LM.LEFT_ANKLE,
                'r_ankle': self.LM.RIGHT_ANKLE
            }
            
            for key, lm_enum in mapping.items():
                coords[key] = self.get_point(landmarks, lm_enum)
                if coords[key]:
                    correct_joints.add(key) # Add to correct initially
            
            # --- 1. DETECT MODE ---
            self.current_mode = self.detect_mode(coords)
            if self.current_mode == "UNKNOWN":
                return image, ["Not Enough Landmarks Visible"]
                
            # --- 2. DETECT VIEW ---
            self.current_view = self.detect_view(coords)
            
            # --- 3. DETECT POSITION ---
            self.current_position = self.detect_position(coords, self.current_view)
            
            # --- 4. ANALYZE UPPER BODY ---
            self.detect_upper_body_posture(coords, issues, problematic_joints)
            
            # --- 5. ANALYZE FULL BODY ---
            if self.current_mode == "FULL_BODY":
                self.detect_full_body_posture(coords, issues, problematic_joints)
                
            # Filter correct joints list
            for j in problematic_joints:
                if j in correct_joints:
                    correct_joints.remove(j)
                    
            # --- 6. VISUALIZATION ---
            self.draw_visualization(image, landmarks, issues, correct_joints, problematic_joints, coords)
            
        else:
            issues = ["No Person Detected"]
            
        return image, issues

    def draw_visualization(self, image, landmarks, issues, correct_joints, problematic_joints, coords):
        h, w, c = image.shape
        
        # Draw basic pose lines in faint color
        self.mp_drawing.draw_landmarks(
            image, landmarks, self.mp_pose.POSE_CONNECTIONS,
            self.mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=1),
            self.mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=1)
        )
        
        # Key to Enum Mapping
        joint_mapping = {
            'nose': self.LM.NOSE,
            'l_ear': self.LM.LEFT_EAR,
            'r_ear': self.LM.RIGHT_EAR,
            'l_shoulder': self.LM.LEFT_SHOULDER,
            'r_shoulder': self.LM.RIGHT_SHOULDER,
            'l_hip': self.LM.LEFT_HIP,
            'r_hip': self.LM.RIGHT_HIP,
            'l_knee': self.LM.LEFT_KNEE,
            'r_knee': self.LM.RIGHT_KNEE,
            'l_ankle': self.LM.LEFT_ANKLE,
            'r_ankle': self.LM.RIGHT_ANKLE
        }
        
        # Highlight Proper / Correct Joints (GREEN)
        for j_name in correct_joints:
            lm = landmarks.landmark[joint_mapping[j_name]]
            cv2.circle(image, (int(lm.x * w), int(lm.y * h)), 5, (0, 255, 0), -1)

        # Highlight Problematic Joints (RED)
        for j_name in problematic_joints:
            if j_name in joint_mapping:
                lm = landmarks.landmark[joint_mapping[j_name]]
                cv2.circle(image, (int(lm.x * w), int(lm.y * h)), 8, (0, 0, 255), -1)
                
        # Draw Spine Alignment Line (Mid-Shoulder to Mid-Hip)
        mid_sh = self.mid_point(coords['l_shoulder'], coords['r_shoulder'])
        mid_hip = self.mid_point(coords['l_hip'], coords['r_hip'])
        if mid_sh and mid_hip:
            pt1 = (int(mid_sh[0] * w), int(mid_sh[1] * h))
            pt2 = (int(mid_hip[0] * w), int(mid_hip[1] * h))
            cv2.line(image, pt1, pt2, (255, 255, 0), 2) # Cyan line for spine

def main():
    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    detector = PostureDetector()
    
    print("============================================")
    print("Real-Time Multi-Angle Posture System")
    print("============================================")
    print("Press 'q' to quit")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            break

        # Calculate FPS
        cTime = time.time()
        fps = 1 / (cTime - detector.pTime) if detector.pTime > 0 else 0
        detector.pTime = cTime

        image, issues = detector.process_frame(frame)
        
        # --- UI Overlay ---
        cv2.rectangle(image, (0, 0), (500, 160), (0, 0, 0), -1)
        
        cv2.putText(image, f"Mode: {detector.current_mode}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(image, f"View: {detector.current_view}", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(image, f"Pos:  {detector.current_position}", (10, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(image, f"FPS:  {int(fps)}", (10, 120), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
        # Posture Status
        y_offset = 150
        if not issues:
            cv2.putText(image, "GOOD POSTURE", (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            cv2.putText(image, "ISSUES DETECTED:", (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.rectangle(image, (0, 160), (500, 170 + 30*len(issues)), (0,0,0), -1)
            for idx, issue in enumerate(issues):
                y_offset += 30
                cv2.putText(image, f"- {issue}", (10, y_offset), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imshow('Real-Time Posture Detection System', image)

        # Keyboard Controls
        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
