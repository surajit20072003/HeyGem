import sys
import os

try:
    from moviepy.editor import VideoFileClip, vfx
except ImportError:
    print("Error: 'moviepy' library is not installed.")
    print("Please install it running: pip install moviepy")
    sys.exit(1)

def remove_background(input_path, output_path, color_rgb=(0, 255, 0), threshold=100, stiffness=5):
    """
    Removes a specific color (green screen) from a video and saves it with transparency.
    
    Args:
        input_path (str): Path to input MP4 file.
        output_path (str): Path to output file (must be .webm or .mov).
        color_rgb (tuple): The color to remove, default is Green (0, 255, 0).
        threshold (int): minimal euclidean distance between matched matching color.
        stiffness (int): Defines the smoothness of the mask.
    """
    
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        return

    print(f"Processing: {input_path} -> {output_path}")
    print("This might take a while depending on the video length...")

    try:
        # Load the video clip
        clip = VideoFileClip(input_path)
        
        # Apply the color mask (chroma key)
        # 0,255,0 is bright green. You might need to adjust this if your green is darker.
        # thr (threshold) determines how close a color must be to the target green.
        # s (stiffness) determines the smoothness of the mask edges
        masked_clip = clip.fx(vfx.mask_color, color=color_rgb, thr=threshold, s=stiffness)
        
        # Ensure the output has an alpha channel (transparency)
        # WebM with VP9 usually handles transparency well.
        if output_path.lower().endswith('.webm'):
            print("Encoding to WebM (VP9)...")
            masked_clip.write_videofile(output_path, codec='libvpx-vp9', audio_codec='libvorbis', logger='bar', verbose=False)
        elif output_path.lower().endswith('.mov'):
            # ProRes 4444 supports alpha
            print("Encoding to MOV (ProRes 4444)...")
            masked_clip.write_videofile(output_path, codec='prores_ks', audio_codec='aac', logger='bar', verbose=False)
        else:
            print("Warning: Output format might not support transparency. Recommended: .webm or .mov")
            masked_clip.write_videofile(output_path, codec='libvpx-vp9', logger='bar')
            
        print("\nDone! Video saved with transparency.")
        print(f"Saved to: {output_path}")
        
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python remove_greenscreen.py <input_video.mp4> <output_video.webm> [threshold]")
        print("Example: python remove_greenscreen.py my_video.mp4 output.webm 100")
        print("\nNote: 'threshold' controls how much green is removed (default 100). Increase if green outlines remain.")
        sys.exit(1)
        
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    
    # Check if user provided a custom threshold
    thr = 100
    if len(sys.argv) > 3:
        try:
            thr = int(sys.argv[3])
            print(f"Using custom threshold: {thr}")
        except ValueError:
            print("Invalid threshold value. Using default 100.")
            pass
            
    remove_background(in_file, out_file, threshold=thr)
