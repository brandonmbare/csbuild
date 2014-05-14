//Make sure both c and c++ includes are working correctly
#include "stdio.h"
#include <string>

int main()
{
	puts(std::string("Hello, world!").c_str());
}