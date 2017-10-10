<div style="max-width: 1000px">
<h1>Simple Midi Converter</h1>
<h2>Overview</h2>

The goal of this project is to build a collection of strategies that can be used to convert raw audio data into musical notes (.midi files). This project is currently in its very early stages.

A .midi file stores the notes of a musical piece as time-based events. It is very similar to music sheet, where the musician would be a midi synthesizer software. There are many existing software that can convert raw audio files into .midi files. The purpose of this project is to develop an interesting collection of conversion strategies.

<h2>Usage</h2>

Currently, the project is very primitive and can only be run through the command line.
Only 2 files are tested with the code so far, and are stored in the audio/ folder. Check out testScript.py for some ways to run the project. .midi files will are generated in the output/ folder. Check out the samples folder for midi files generated with by this project. As well, checkout demoResources for a visualisation of the development process. The midi synthesizer I use is Synthesia, but any synthesizer that supports the time-coded midi format would work for playing the .midi file.

http://www.synthesiagame.com/


<h2>Technical Details</h2>
This section is a blog-style explanation of the progress and thinking of the project so far.

This project primarily uses ideas from Digital Signal Processing (DSP) to perform note detection. The prevalent concept used is Fast Fourier Transforms (FFT). The FFT will transform audio samples in time domain into magnitude samples in frequency domain. The <i>amplitude vs time</i> data present in raw audio files will be transformed to <i>magnitude vs frequency</i> data and used in analysis.

The goal is to convert a raw music file into a set of notes to be played (for now, just generic piano notes). It would convert a raw audio like this:
<p align="center">
	<audio controls>
		<source src="demoResources/Ltheme2Demo.mp3" type="audio/mp3">
		<source src="demoResources/Ltheme2Demo.wav" type="audio/wav">
		<a href="demoResources/Ltheme2Demo.mp3" download="LthemeDemo.mp3">Ltheme Demo (I currently don't host these files, they are in the repo.)</a>
	</audio>
</p>
into a midi file (rendered in Synthesia) like this:
<p align="center">
	<video width="320" height="240" controls>
		<source src="demoResources/SynthesiaDemo.mp4" type="video/mp4">
		<a href="demoResources/SynthesiaDemo.mp4" download="SynthesiaDemo.mp4">Rendered Midi File</a>
	</video>
</p>
Of course, you can see that in the case of the midi file, there are a lot of "false" notes present. The ideal midi file would consist of only the notes that are audibly present in the sound file and nothing more. However, the challenge to this problem (aside from the main technical challenges) is that musical note perception is not purely a physiological phenomenon but a psychological one as well. The current state of the project examines some ways the conversion from raw audio to notes can be done without machine learning.

<h3>Windowing</h3>
The first approach uses a simple idea in DSP known as windowing. As we know, the FFT of a series of sound samples tells us the frequencies present in it. However, it does not tell us the <i>frequency vs time</i> information within the time range the FFT operated on. This means to arrive at the <i>time vs frequency</i> data, we would need to make some sort of estimation. The windowing function is a technique where we divide the main audio into many time intervals each the length of the "window size". The FFT of the audio samples in each time interval is calculated. We would then know the frequencies present in each time interval (or each window). Selecting small time intervals gives us precise enough time information for audio to note conversion. The result of this process with respect to the sample audio is shown below.
<p align="center">
	<image src="demoResources/DiscreteProcessor1.png" width="600"/>
	<p align="center">Fig. 1</p>
</p>
<p>
In the image, a person can heuristically tell what the musical notes are through time just by looking at the shapes. Keep in mind however, that this is a very simple audio simple, with only one instrument playing notes at any given time. But we will start our analysis with this simple idea.
</p>

<p>
To generate the image (or rather, 2D-array), we use a reasonable window size of 2205 samples for a audio file with a sample rate of 44100. The audio file is split into 2205-sized chunks and FFT is calculated for each chunk. The FFT are then lined up, each as a row to a 2d array, and the values are displayed as a height map.
</p>

<p>
Next, logic is needed to discern which pixels of the image constitute a note. I look for the shapes by starting at each local maxima of the image. One assumption made is that each shape is 2 pixels wide, which comes from the fact that the single frequency of a note can only be at most 2 pixels wide if it were to lie in the middle of the 2 frequencies represented by the columns. The height of the shape is determined by an algorithm that looks for big decreases in value, among other lesser properties. The exact frequency of each note can then be estimated by taking the "center of mass" of the shape, which uses the value of each pixels as weight and column indices as value. The time can be estimated as well using the rows the shape starts and ends at. The result of this is a rough estimation of notes that are played.
</p>

<p>
One thing to consider about music is the multi-harmonic nature of the notes. As can be seen in Fig. 1, which is the frequency representation of a monophonic audio file, multiple frequencies are present at any given time. The simultaneous shapes (with respect to time) are the harmonics that compose a note. All harmonic frequencies of a given note are integer multiples of the base harmonic. However, it can be hard to tell whether a set of harmonics is a single note or multiple notes exactly 1 octave apart (since frequencies double per octave). In this approach, we simply combine all harmonics found into the base harmonic.
</p>

<p>
The result of this approach is something that can match the general feel of the music piece. There are always rules or techniques that can be implemented on this idea to improve its performance, but there is a major flaw with the base idea of windowing: precision.
</p>

<p>
In the scope of this use case, we care about both frequency and time precision. However, while a smaller window size will increase time precision, it will also decrease frequency precision. There is no compromised value that will work to detect the lowest of notes while still maintaining decent time precision. While I do acknowledge that there are ways to improve precision using other techniques, I personally believe that a shift in the base idea of windowing will be a better approach.
</p>

<h3>Continuous Windowing</h3>
<p>
This approach uses the basic idea of windowing but with a twist. This is somewhat of an original idea although I'm not sure if there is something similar out there (I don't know what to search for after all). The idea is to use FFTs in a more continuous way rather than in big chunky windows, so that you increase both time and frequency precision. Before the whole idea is explained, here is a preview of what the <i>frequency vs time</i> height map would look like:
</p>

<p align="center">
	<image src="demoResources/ContinuousProcessor1.png" width="600"/>
	<p align="center">Fig. 2</p>
</p>

<p>
Vertical blue lines are drawn to denote the exact frequency the musical notes are defined to be (using equal-tempered scale) and yellow lines are drawn where the <i>frames</i> are.
</p>

The fundamental idea used in this method revolves around using the definition of an FFT in an approximate fashion. A FFT transforms time domain info to frequency domain info and it does this by decomposing a complex waveform into sine waves of different frequencies. A naive way to look at the FFT definition suggests that you can look at overlapping windows of FFT and determine the frequencies of the non-overlapping component.

<p align="center">
	<image src="demoResources/FFT1.png" width="600"/>
	<p align="center">Fig. 3</p>
</p>

<p>
Taking a look at Fig. 3, where A, B, C, D are all time domain samples, it can be said that FFT(B) - FFT(A) roughly equals FFT(D) - FFT(C). The logic behind this statement has some basis. We may intuitively expect that the FFT of overlapping section have the exact same frequencies present, leaving the difference in frequencies of A and B to be the non-overlapping section. However, this is not true due to the discrete nature of FFTs.
</p>

<p>
First, it is important to note that the raw data fed into the FFT function is not continuous, but discrete samples (44100 Hz). In this sense, the resulting FFT will also be a discrete approximation of the continuous frequencies present in the sound. The continuous windowing idea further reduces the accuracy of the approximation because it is calculating the FFT of a sub-chunk of waveform, without consideration for surrounding data. In essence, the FFT of the sub-chunk will be slightly different from its actual frequency contribution to the greater waveform that envelops it. What the difference is is less important and much less complicated than the approximation we will use to account for this.
</p>

<p>
To begin the algorithm, we will zero-pad the original audio samples from the left so that we can make estimations easier (The C-chunk's FFT in Fig. 3 for the zero-padded samples can be estimated to be 0). Then, we can calculate the D-chunk directly using D = B - A + C. The D chunk's FFT values are tied to a very narrow chunk of time while its values are calculated using a large chunk (A) of time. Thus, we can obtain time precision as if the window size was the length of D and frequency precision as if the window size was the size of A. Calculating D chunks this way will yield the following values:
</p>

<p align="center">
	<image src="demoResources/ContinuousProcessor3.png" width="600"/>
	<p align="center">Fig. 4</p>
</p>

<p>
This time, there are negative values present in the 2D array. As well, we can see the presence of minor artifacts that would interfere with algorithms operating on this data. To get rid of the negatives, we try to interpret their meaning and account for them accordingly.
</p>

<p>
Essentially, it does not make sense to have a negative magnitude for an FFT. With the way we are calculating each row of FFT, there are approximation errors. Negatives will exist in the case where the previous rows reported a magnitude that overshot the actual value, then the future rows will be the ones correcting this mistake (since future rows work with more samples, we will deem it to be more accurate). We can essentially propagate all negative values up the columns to imitate this correction (imagine shoving sand into a series of holes, negative numbers being the height of the sand and positive numbers being the depth of the holes). The current algorithm uses 0 as the "neutral" value but a background-noise value can be used instead to increase accuracy. Overall, this idea is still an approximation, but increases accuracy greatly and eliminates a lot of unwanted artifacts. As well, increased degrees of precision also increases runtime, since we are computing much more FFTs. For a generic comparison, the accuracy shown in Fig 2. takes roughly 5 times the processing time of Fig 1.
</p>

<p>
After the initial set of unwanted artifacts are filtered out, it was observed that there is error carry-over given the approximation nature of the algorithm. To combat this, frames are introduced. The original audio sample will be split into many frames. The algorithm to populate the 2d array will operate on each frame independently and the results are combined. This way, there is no error carry-over between frames. Again, in Fig. 2,  the frames are outlined in yellow.
</p>

<p>
The main thing that is left is to do note selection. Since there are many more data points to work with during analysis, a strategy is needed to reduce runtime. The strategy used in the current algorithm is to calculate which columns particular notes would be found and only analyse in proximity of the columns. Since notes will often be slightly off tune, the search range is temporarily expanded when parts of an off tune note is detected.
</p>

<p>
To find exact notes, the values of the columns corresponding to potential notes are scanned. The approximate location of a note is detected by linearly looking for large bumps (areas of similar values that are larger in magnitude than their surrounding) in the 2d array.  Ideas from Jenks natural breaks optimization are used to implement a simplified natural breaks detection algorithm, which decides on the exact start and end of the note.
</p>

<p>
The results of this analysis yields the midi (piano notes) file presented at the beginning of this document.
</p>

<p>
It should be noted at this point that although there are some unwanted notes in the midi file, the core-notes are very crisp and clear and that fine tuning of the main algorithm (which is being worked on) should allow much better filtering. The point being that the 2d array with frequency values is very clear. But taking a look at a more complex music sample, more problems are introduced.
</p>


<p align="center">
	<image src="demoResources/ContinuousProcessor2.png" width="600"/>
	<p align="center">Fig. 5</p>
</p>

Fig.5 is the 2d value array for the first few seconds of Sia's Chandelier. As can be seen, the shapes present are a lot less consistent with each other. The loss of consistency is attributed mostly to the nature of human vocals, where every other note sung by a human can have a different "feel" to it. At this point, a more generic or all-catching algorithm is perhaps needed to detect notes in audio files as complex as this one. Of course, this is not as complicated as audio file get.

<h3>Continuous Windowing with Recursive Weight Distribution</h3>

Another idea of interest I've tried involves replacing the original 2d value array generating algorithm with a slightly different one. The new algorithm lowers the amount of unwanted artifacts by a decent amount. The idea is to first get all the frequencies present in a single frame. The frequencies will be recursively subdivided into the top and bottom half of the frame, with the division ratio being the FFT of the top half vs the FFT of the bottom half. The following Fig. 6 shows the results of the recursive frequency distribution.

<p align="center">
	<image src="demoResources/ContinuousProcessor4.png" width="600"/>
	<p align="center">Fig. 6</p>
</p>

As can be seen, the conic shape of notes is gone, as well as the fragmentation at the end of notes. This makes the 2d array a lot clearer. However, new artifacts are introduced, such as the sharp row-to-row transition where some subdivisions occur. It should note that this method is significantly slower since instead of being a linear order of precision, it is now n(log n) of precision because of the recursive FFTs that must be performed. In practice, this is approximately 5 times slower than regular continuous windowing.	

</div>