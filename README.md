<h1>Simple Midi Converter</h1>
<h2>Overview</h2>

The goal of this project is to build a collection of strategies that can be used to convert raw audio data into musical notes (.midi files). This project is currently in its very early stages.

A .midi file stores the notes of a musical piece as time-based events. It is very similar to music sheet, where the musician would be a midi synthesizer software. There are many existing software that can convert raw audio files into .midi files. The purpose of this project is to develop an interesting collection of conversion strategies.

<h2>Usage</h2>

Currently, the project is very primitive and can only be run through the command line.
Only 2 files are tested with the code so far, and are stored in the audio/ folder. When testScript.py is run, a .midi file will be generated along with .png for debug purposes in the output/ folder. The current output of the 2 test files are commited to the samples/ directory. The midi synthesizer I use is Synthesia, but any synthesizer that supports the time-coded midi format would work for playing the .midi file.

http://www.synthesiagame.com/


<h2>Technical Details</h2>
This section is a somewhat detailed explanation of the progress and thinking of the project so far.

The goal is to convert a raw music file into a set of notes to be played (for now, just generic piano notes). It would convert this:
<audio controls>
  <source src="audio/Ltheme2Demo.wav" type="audio/wav">
  <source src="audio/Ltheme2Demo.mp3" type="audio/mp3">
Your browser does not support the audio element.
</audio>
into this:

