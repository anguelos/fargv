I want you to read and write in you directory, employ git only passively, run pytest and sphix.
Consider your self restricted, I am going to be manually managing git, and manually running any pip commands, including setup.py install ...

This directory already contains a very brief outline of the project.
Read all of these instructions before implementing anything.
Ask me step-by-step questions on any clarifications you might need.
If you see an instruction that seems ambiguous or suggests a poor design pattern / choice. Suggest alternatives but be brief.

Your modus operanti:
I want you to maintain .claude/DESIGN.md where you will be storing design patterns favored in the project, as well a conventions, decisions etc... .claude/DESIGN.md should be able to work as a prompt that will as much as possible function like a resume session.
Any instuction requires you to run a command you are not authorized offer me the option to add to your list of available commands.
If not sure ask me quick step by step questions.
Accessing files/pages on the internet should only be done with my explicit permission.
This file (.claude/CLAUDE_INITIAL.md) should stay immutable.
Whenever an instruction overides this text update file (.claude/CLAUDE_MODIFIED.md) ideally a meld or a diff should be informative of the evolution of the project, both you and me can use .claude/CLAUDE_MODIFIED.md to register the present state or require updates to the project.
You should only handle git passively, I will manage any git instructions.
You should only handle pip passively, ask me to run any pip instruction you need.


Python coding:
Entry point functions should always start with def main_
Docstrings must be numpy strings contain Inputs, Return Values, Raised Exceptions, code snippets for examples etc. In general when prototyping dont implement the automatically, avoid implemeting them when scafolding, Implement them when explicitly asked for it.
As with docstrings, when scaffolding code you should avoid extencive typehints. But when asked to make code more formal or to produce docstrings, add typehints beeing as specific as possible. Use python's standard typing module and its type constructs such as Optional,List,Tuple,Dict, generator etc...

Python project structure:
I want you to create a setup.py that will be the main tool realising the deployment instalation etc. In the setup.py be as extencive in requirements.
Create a minimum pyproject.toml which will delegate as much as possible to setup.py and contain linting information for ruff, the allowed linewidth will be 160 characters.
Add a requirements.txt that will be enough to install a proper development python environment.
Set the project license to the MIT public licence.
Add a test directory where every kind of test case will have its onw directory among which specifcally a test/unittest subdirectory. The test cases should be implemented with pytest. Unittests should be used for coverage and they should maximize coverage of ./src/ but exclude all entry points (def main_....) when computing coverage.
Add a docs subdirectory which will use sphinx to render documentation. The documentation will be using markdown instead rst files. It will be offering an API description, command line tools documentation, a quickstart guide etc... The documentation  will eventually be published in RTD so prefer its style. Employ popular features such as copying code and linking to source code.
create a Makefile that will allow to: 
    1)"make clean": erase all build files as well as .pyc files, .egg-inf etc..
    2)"make build": builds the file for deployment to pypi (erases out of data files in )
    3)"make doc", "make htmldoc": build sphinx for html output
    4)"make pdfdoc": build sphinx for single pdf output
    5)"make test": runs all testcases but exits on the first failure.
    6)"make testfull" runs all testcases but doesnt exit on the first failure.
    7)"make unitest" runs all only unitests and print coverage
    8)"make testlint" treats linting errors as errors
    9)"make autolint" autolints all python code in the project.
create a .gitignore apropriate for python that will also exclude .pypi_token and any directory or subdirectory called tmp.
create a pyproject.toml but delegate as much as possible to setup.py, use pyproject.toml for code style and linting information, set the character linewidth to 160.
Create and maintain a README.md, among other things it should contain shields with test coverage, test passing, number of downloads, reposize, python versions, and anything you might find relevant.

Fargv types in legacy implementation:
string (int): the most general
bool (int): when defaulting to False acts as a switch parameter.
int (int): an integer
float (float): an integer
positional (set): a collection of things typically a filelist frequently used with wildcards. The unoredered design was to guarantie independence of input order in order to facilitate parallelism, I dont like it anymore as users have complained it is to limiting.
choice (tuple): a limited set of strings strings among which someone can choose, the first one beeing the default value.



Project outline:
In this repo I want to create a major upgrade to my legacy code in https://pypi.org/project/fargv/.
Familiarize your self with it's code its core ideas.
The legacy functionallity is implemented in @fargv/fargv_legacy.py and exposed as fargv.fargv Backward compatibillity is of the outmost importance.
I want to implement the new version in a more organised fashion.
New features I want to add:
* while still encouraging default parameters in general, allowing parameters that must be set.
* make a gui window with those preferences.
* employ fargv as google flame arg parser, turning any function to a potential entry point.
* automatic help generation
* automatic bash autocomplete generation
* Allow more types of parameters such existing files, non-existing files, custom types, sub commands.
* Allow intermediary representation of suppported fargv types.
* Allow parsing configuration files (in varius formats) to overide the defaults given in the source code.
* Allow for postionals that are implicitly named.
* Allow for dynamic mode where parameters to be updated from external sources during runtime eg: by modifying a config file or changing a value in a gui.
* Become more interoperable with other popular tools.
* Allow for a uniform way to handle stream parameters so users can redirect to stdout or write to a file.
* Have a consistent way to handle verosity which might play well tools such as logging etc.
* Allow to read system variables in order to overide defaults.

Design princips:
1)Parameter type/limitations can be automaticaly infered by the default value.
2)Any key-value pair can be validated for compliance
3)A list of strings such as sys.argv can also be used to infer key-values and compliance.

How I want you to proceed:
1)Make shure the local settings .json in .claude allows you to implement all these instructions.
2)Create scaffold code for all modules and entry points
3)Create the project files I mentioned earlier.
3)Create simple unittests providing minimal coverage to the modules.
4)Create sphinx documentation
5)Update .claude/CLAUDE_MODIFIED.md
