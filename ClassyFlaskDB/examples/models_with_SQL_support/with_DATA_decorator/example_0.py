from ClassyFlaskDB.DATA import DATA, DATAEngine

from dataclasses import dataclass, field

from typing import List

@DATA
class Bar:
    id: str

@DATA
class Bar2(Bar):
    name: str

@DATA
class Foo:
    id: int
    bar: Bar
    bars: List[Bar] = field(default_factory=list)
    
DATA.finalize()
data_engine = DATAEngine(DATA, engine_str='sqlite:///my_database3.db')

# Example usage
bar_instance = Bar(id='bar1')
foo_instance = Foo(id=1, bar=bar_instance)
foo_instance.bars.append(Bar(id='bar2'))
foo_instance.bars.append(Bar(id='bar3'))
data_engine.merge(foo_instance)

bar_instance = Bar2(id='bar4', name='Bar 4')
foo_instance = Foo(id=2, bar=bar_instance)
foo_instance.bars.append(Bar2(id='bar5', name='Bar 5'))
foo_instance.bars.append(Bar(id='bar6'))
data_engine.merge(foo_instance)

import json
print(json.dumps(foo_instance.to_json(), indent=4))

# Query
with data_engine.session() as session:
    queried_foo = session.query(Foo).filter_by(id=1).first()

    print(json.dumps(data_engine.to_json(), indent=4))
    if queried_foo and queried_foo.bar:
        print(f"Foo ID: {queried_foo.id}, Bar ID: {queried_foo.bar.id}")
    else:
        print("Foo or associated Bar not found")