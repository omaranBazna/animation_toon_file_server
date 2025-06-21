from merge_two_videos.put_video_on_bg import put_video_on_background
from merge_two_videos.make_video_with_opacity import make_video_with_opacity,make_video_with_mask
from merge_two_videos.merge_videos import merge_videos
import numpy as np
def prune_sandwiched_zeros(arr1, arr2, iterations=30):
    output1=[]
    output2=[]
    # Ensure arrays are the same length
    max_len = max(len(arr1), len(arr2))
    arr1 = np.pad(arr1, (0, max_len - len(arr1)), constant_values=0)
    arr2 = np.pad(arr2, (0, max_len - len(arr2)), constant_values=0)

    arr1 = np.array(arr1, dtype=int)
    arr2 = np.array(arr2, dtype=int)

    for iteration in range(iterations):
        current = arr1 if iteration % 2 == 0 else arr2
        other = arr2 if iteration % 2 == 0 else arr1

        new_array = current
        for i in range(len(current)):
            if current[i] == 0 or current[i] == -1:
                
                if(i-1>0):

                    #print(current[i-1])
                    if(current[i-1]==1 and other[i-1]==1):
                        current[i-1]=0

                if(i+1<len(current)):
                    if(current[i+1]==1 and (i+1==len(other) or other[i+1]==1)):
                        current[i+1]=0

        if iteration % 2 == 0:
            output1=current
        else:
            output2=current



    return output1,output2

def merge_two_videos_into_one(video_path1,video_path_2,bg_1,bg_2,final_output_path):
    
    
    video_path = video_path1
    background_path = bg_1
    final_output_path_1 = "video_path1.mp4"
    put_video_on_background(video_path, background_path, final_output_path_1)
    mask_1 = make_video_with_opacity(final_output_path_1)


    video_path = video_path_2
    background_path = bg_2
    final_output_path_2 = "video_path_2.mp4"
    put_video_on_background(video_path, background_path, final_output_path_2)
    mask_2 = make_video_with_opacity(final_output_path_2)


    Mask_1,Mask_2 = prune_sandwiched_zeros(mask_1,mask_2)


    with open("frames.txt", "a") as fb:
        fb.write(str(Mask_1.tolist()) + "\n")  # Write as list and add newline
        fb.write(str(Mask_2.tolist()) + "\n")  # Write as list and add newline




    make_video_with_mask(final_output_path_1,final_output_path_1,Mask_1)
    make_video_with_mask(final_output_path_2,final_output_path_2,Mask_2)

    merge_videos(final_output_path_1,final_output_path_2,final_output_path)
