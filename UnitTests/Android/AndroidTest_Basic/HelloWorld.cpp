//Make sure both c and c++ includes are working correctly
#include "stdio.h"
#include <string>

//int main()
//{
//	puts(std::string("Hello, world!").c_str());
//}

#include <android/log.h>
#include <android_native_app_glue.h>
#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "NativeActivitySimpleExample", __VA_ARGS__))
 
void android_main(struct android_app* state)
{
	LOGI(std::string("Hello, World!").c_str());
}