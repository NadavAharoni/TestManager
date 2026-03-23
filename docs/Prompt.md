# Initial Prompt

I am a teacher. I would like to create a tool to help me manage exams.

Mainly multiple choice tests.
Some tests I have to print, some become Moodle quizes.

Some questions have images, formulas, diagrams, code snippets, tables, etc.

I want to write in textual format. It can be md, but I also need to be able to set specific fonts and layouts, so I'm not sure that md is rich enough. I'm open to other options (maybe AsciiDoc?).

Most of my tests are multiple choice. Some have just one correct choice, and others can have a list of statements, and the students have to make which statements are correct. The get points for each correct statement that they mark as correct, and they get negative points for each incorrect statement that they mark as correct.

The statements can also have rich text, math, diagrams, etc.

Most of the exams that I author are in Hebrew. In practice it means that the test include Hebrew text, and also equations, code, and statements that include English text. There is no Hebrew text inside equations.

I want to adopt or design a format for storing the questions and answers.

I think that each question can be in it's own directory. The directory will include the question in md, or whatever format we will choose.
Then each answer will be in it's own file, which will include the answer, plus an indication if it's correct or not.
There can also be a "grading formula" for the question which might indicate that not every answer contributes the same.
For example, one statement can be very wrong and have a big negative grade, while another can be just "slightly wrong" and have a smaller penalty.
Images can be in the same directory.

Another option is to have each question with all the answers in one json file.
But in any case I think that images will be in a separate file, so a multi-file approach is reasonable IMO.

I will want python code that can generate either pdf, or xml which is compatibe with moodle.

An extra bonus would be code that extracts questions form Word documents.
In my experience it's difficult, so I'm ok with some manual work here.



I
