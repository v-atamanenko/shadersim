# ShaderSim

Simple Python script to determine which one of your 3913403248 shaders
disassembly is being displayed in Razor.

<center>
    <img src="https://user-images.githubusercontent.com/11796486/222990372-ea96358c-b094-4dc3-8b7e-a8ec829690ab.png">
</center>

## How to use:
1. Get python 3.6+
2. Install requirements via `python3 -m pip install -r requirements.txt`
3. Put your .gxp shaders into `./shaders_gxp`.
4. Put your disasm from Razor into `./input.txt`. Don't worry about formatting.
5. Put `psp2shaderperf.exe` into `./`.
5. Run the script with `python3 shadersim.py`.

## How to read the output:
1. The bigger the value, the more similar this shader is to your input.
2. If there's one shader with value > 100, it’s the one.
3. If there are several items with value > 100 probably there are extremely
similar/duplicate shaders and you may need to compare the output by eye
(unless there is one significantly bigger value like 150 or 200, then this one
is the one).
4. <100 is garbage and too different.
