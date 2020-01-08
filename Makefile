# Need targets:
#	help
#	simulate module
#       simulate all
#       verify module
#       simulate all
#       program app
#	clean

help:
	@echo No help.

sim-%:
	echo $(MAKECMDGOALS)

foo:
	echo $(MAKECMDGOALS)

clean:
	@set -e;							\
	find * -name \*.gtkw -o -name \*.vcd                            \
	| while read f;		                                        \
	do								\
	    echo rm -f $$f;						\
	    rm -f "$$f";						\
	done
	@set -e;							\
	find * -type d \( -name build -o -name __pycache__ \)		\
        | while read d;							\
	    do								\
	    echo rm -rf $$d;						\
	    rm -rf "$$d";						\
	done


.PHONY: help clean
