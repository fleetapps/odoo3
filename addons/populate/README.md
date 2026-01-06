# Populate

Generate synthetic data for an Odoo database following a predefined 
**Blueprint**.

Useful for performance testing, demos, and development environments.

## Quick Start

```shell
odoo-bin populate -d <database> -b <blueprint>
```

| Option             | Description                                                 |
|--------------------|-------------------------------------------------------------|
| `-d <database>`    | Target database (required)                                  |
| `-b <blueprint>`   | Blueprint name or full xmlid (required)                     |
| `--scale <factor>` | Multiply all record counts by this factor (default: `1`)    |
| `-j <workers>`     | Parallel processes (`auto` = all CPU threads, default: `1`) |
| `--resume [id]`    | Resume the last (or a specific) interrupted session         |

### Examples

```shell
# Run a blueprint at 10x scale using all cores
odoo-bin populate -d mydb -b project.service_company_blueprint --scale 10 -j auto

# Resume the last interrupted session
odoo-bin populate -d mydb --resume
```

## Blueprints

A Blueprint is a record of `populate.blueprint` that describes **what
data to create** in a
declarative XML (or JSON) definition. Blueprints are typically shipped
inside a module's
`populate/` folder and loaded automatically when the `populate` module
is installed or upgraded.

### XML Structure

A blueprint definition is a list of `<model>` blocks, each containing
`<field>` declarations:

```xml
<model name="res.partner" count="500" id="my_partners">
    <field name="name" generator="fake.company" null_frac="0"/>
    <field name="email" generator="fake.company_email"/>
    <field name="active" eval="True"/>
</model>
```

#### `<model>` Attributes

| Attribute  | Required     | Description                                                          |
|------------|--------------|----------------------------------------------------------------------|
| `name`     | yes          | Odoo model technical name (e.g. `res.partner`)                       |
| `count`    | for `create` | Number of records to create                                          |
| `id`       |              | Reference tag - lets later blocks target these records               |
| `type`     |              | `create` (default) or `write`                                        |
| `ref`      | for `write`  | Reference to a previously created batch (its `id`)                   |
| `scale`    |              | `True` (default) / `False` - whether `--scale` applies to this block |
| `parallel` |              | `True` (default) / `False` - whether the job can run in parallel     |
| `context`  |              | Python dict literal merged into the ORM context                      |

#### `<field>` Attributes

| Attribute      | Required | Description                                                                               |
|----------------|----------|-------------------------------------------------------------------------------------------|
| `name`         | yes      | Field name on the model                                                                   |
| `generator`    | (1)      | Generator to use (see table below)                                                        |
| `eval`         | (1)      | A Python expression - static value or dynamic expression referencing other fields         |
| `null_frac`    |          | Probability of generating `False` (0-1, default `0.3`; forced to `0` for required fields) |
| `unique`       |          | `True` to enforce uniqueness across the database                                          |
| `values`       |          | Explicit value list or weighted dict, e.g. `"{'a': 3, 'b': 1}"`                           |
| `distribution` |          | Statistical distribution, e.g. `"normal(mean=50, std=10)"`                                |
| `domain`       |          | ORM domain to filter related records (for relational generators)                          |
| `ref`          |          | Restrict relational picks to records created under this reference                         |
| `virtual`      |          | `True` to mark as a virtual (non-persisted) intermediate field                            |

> (1) Either `generator` or `eval` must be provided. If `generator` is
> not set, `eval` is
> assumed (i.e., the `misc.eval` generator).

## Generators

### Scalar

| Generator        | Field Types | Key Params          |
|------------------|-------------|---------------------|
| `scalar.boolean` | `boolean`   | `values` (weighted) |
| `scalar.integer` | `integer`   | `start`, `end`      |
| `scalar.float`   | `float`     | `start`, `end`      |

### Textual

| Generator      | Field Types    | Key Params           |
|----------------|----------------|----------------------|
| `textual.char` | `char`, `html` | `length`, `char_set` |
| `textual.text` | `text`, `html` | `length`, `char_set` |

### Temporal

| Generator           | Field Types | Key Params                                         |
|---------------------|-------------|----------------------------------------------------|
| `temporal.date`     | `date`      | `start`, `end` (e.g. `"today -6m"`, `"today +1y"`) |
| `temporal.datetime` | `datetime`  | `start`, `end` (e.g. `"now"`, `"now -30d"`)        |

### Choice

| Generator          | Field Types       | Key Params                                           |
|--------------------|-------------------|------------------------------------------------------|
| `choice.selection` | `selection`       | `values` (weighted subset of the field's valid keys) |
| `choice.sample`    | most scalar types | `values` (weighted)                                  |

### Relational

| Generator       | Field Types             | Key Params               |
|-----------------|-------------------------|--------------------------|
| `relation.one`  | `many2one`              | `domain`, `ref`          |
| `relation.many` | `one2many`, `many2many` | `domain`, `ref`, `count` |

### Reference

| Generator       | Field Types          | Key Params                       |
|-----------------|----------------------|----------------------------------|
| `reference.one` | `many2one_reference` | -/- (depends on the model field) |
| `reference.raw` | `reference`          | `res_model`, `res_id`, `ref`     |

### Faker (`fake.*`)

Wraps the [Faker](https://faker.readthedocs.io/en/stable/providers.html) library. Any method
from an allowed provider can be used directly:

```xml
<field name="name" generator="fake.name"/>
<field name="email" generator="fake.email" locale="fr_FR"/>
<field name="phone" generator="fake.phone_number"/>
<field name="bio" generator="fake.paragraph" nb_sentences="5"/>
```

Method-specific keyword arguments (e.g. `nb_sentences`) are forwarded
as-is. Requires `faker` - install from 
`odoo/addons/populate/requirements.txt`.

### Misc

| Generator    | Field Types       | Description                                                       |
|--------------|-------------------|-------------------------------------------------------------------|
| `misc.cycle` | most scalar types | Cycles through `values` in order, deterministically               |
| `misc.eval`  | any               | Evaluates a Python expression; can reference other fields by name |

### Properties

| Generator               | Field Types             | Description                                        |
|-------------------------|-------------------------|----------------------------------------------------|
| `properties.definition` | `properties_definition` | Generates a property schema                        |
| `properties.prop`       | `virtual`               | Helper - defines a single property entry           |
| `properties.value`      | `properties`            | Generates values matching the parent's definition  |

## Distributions

Generators can accept a `distribution` parameter.
Without one, values are picked uniformly at random inside the range. Adding a distribution
lets you control **how likely** certain parts of the range are.

```xml
<field name="age" generator="scalar.integer" start="18" end="90" distribution="normal(mean=35, std=12)"/>
<field name="delay" generator="scalar.float" start="0" end="100" distribution="exponential(rate=0.05)"/>
```

### `normal(mean, std)` - "Most values near the center"

Produces a classic bell curve. Most values land close to `mean`; the 
further from it, the rarer. `std` (standard deviation) controls how 
spread out the curve is - a smaller `std` means values are packed 
tighter around the mean.

**Use when** you want a realistic "average with natural variation"
pattern.

| Example field         | Params                    | Why                                                            |
|-----------------------|---------------------------|----------------------------------------------------------------|
| Employee age          | `normal(mean=35, std=12)` | Most employees are around 35, fewer very young or very old     |
| Product price         | `normal(mean=50, std=15)` | Prices cluster around 50, with some cheaper/expensive outliers |
| Task duration (hours) | `normal(mean=8, std=3)`   | Most tasks take about a day, some shorter or longer            |

### `uniform(min, max)` - "Any value is equally likely"

A flat distribution – every value in the range has the exact same 
chance. This is actually the default behavior when you omit 
`distribution` entirely, so you rarely need to write it out.

**Use when** you genuinely don't want any value to be more common than
another.

| Example field      | Params                     | Why                      |
|--------------------|----------------------------|--------------------------|
| Random color index | `uniform(min=0, max=11)`   | No color should dominate |
| Sequence number    | `uniform(min=1, max=1000)` | Spread evenly            |

### `exponential(rate)` - "Lots of small values, rare large ones"

A steep curve that starts high and drops off. Most generated values 
will be small; large values are increasingly rare. A higher `rate` 
makes it drop off faster (even more concentrated on small values).

**Use when** the data should be skewed toward the low end, with
occasional spikes.

| Example field       | Params                   | Why                                            |
|---------------------|--------------------------|------------------------------------------------|
| Days until deadline | `exponential(rate=0.03)` | Most deadlines are soon, a few are months away |
| Allocated hours     | `exponential(rate=0.1)`  | Most tasks are quick, a few are very long      |
| Time between events | `exponential(rate=0.05)` | Short gaps are common, long gaps are rare      |

### `beta(alpha, beta)` - "Values between 0 and 1, shaped how you want"

Always produces values in [0, 1]. The two parameters shape the curve:

- `alpha=2, beta=2` - bell-shaped, centered at 0.5 (like bounded normal)
- `alpha=1, beta=3` - skewed toward 0 (most values are low)
- `alpha=3, beta=1` - skewed toward 1 (most values are high)
- `alpha=0.5, beta=0.5` - U-shaped, values cluster near 0 and 1

The generator maps this [0, 1] output onto your `start`/`end` range automatically.

**Use when** you're modeling percentages, progress, ratings, or any 
bounded proportion.

| Example field        | Params                  | Why                                                  |
|----------------------|-------------------------|------------------------------------------------------|
| Project progress (%) | `beta(alpha=2, beta=2)` | Most projects are roughly mid-way, few at 0% or 100% |
| Discount rate        | `beta(alpha=1, beta=3)` | Most discounts are small, large discounts are rare   |
| Satisfaction score   | `beta(alpha=3, beta=1)` | Most scores are high                                 |

### `poisson(lam)` - "How many times something happens"

Produces whole numbers representing a **count of occurrences**. 
`lam` (lambda) is the average number of occurrences you expect. 
Values near `lam` are most likely; values far from it are rare.

**Use when** you're generating "how many" – e.g., number of items, 
events, or attempts.

| Example field           | Params           | Why                                             |
|-------------------------|------------------|-------------------------------------------------|
| Number of order lines   | `poisson(lam=5)` | Orders average 5 lines, some have 1, rarely 15+ |
| Support tickets per day | `poisson(lam=3)` | About 3 per day on average                      |
| Login attempts          | `poisson(lam=2)` | Usually 1-3 attempts, occasionally more         |

### `triangular(min, max, mode)` - "I know the best, worst, and most likely"

A simple triangle shape. `mode` is the peak (most likely value), 
`min` and `max` are the absolute bounds. Values near `mode` are 
most common; probability falls off linearly to the edges.

**Use when** you can estimate three points – minimum, maximum, and 
most likely – but don't have more detailed data. This is common for task estimates and cost
projections.

| Example field                      | Params                                | Why                                                        |
|------------------------------------|---------------------------------------|------------------------------------------------------------|
| Task estimate (days)               | `triangular(min=1, max=30, mode=5)`   | Most tasks take ~5 days, never less than 1 or more than 30 |
| Shipping cost                      | `triangular(min=5, max=200, mode=25)` | Typically around 25, bounded by 5 and 200                  |
| Milestone deadline (days from now) | `triangular(min=0, max=120, mode=30)` | Most milestones are about a month out                      |

### Quick decision guide

| You want...                               | Use                                |
|-------------------------------------------|------------------------------------|
| Realistic clustering around an average    | `normal`                           |
| Everything equally likely                 | `uniform` (or omit `distribution`) |
| Mostly small values, rare big ones        | `exponential`                      |
| A percentage / bounded ratio              | `beta`                             |
| A count of "how many times"               | `poisson`                          |
| Three-point estimate (min / likely / max) | `triangular`                       |

## Virtual Fields

Virtual fields are intermediate computation steps that are **not
persisted** to the database.
They let you build values that multiple real fields depend on, avoiding
duplication:

```xml
<model name="account.move.line" count="1000">
    <field name="quantity" generator="scalar.integer" start="1" end="100" null_frac="0"/>
    <field name="price_unit" generator="scalar.float" start="5" end="500" null_frac="0"/>
    <field name="v_subtotal" virtual="True" eval="quantity * price_unit"/>
    <field name="discount" eval="v_subtotal * 0.1 if v_subtotal > 200 else 0"/>
    <field name="price_total" eval="v_subtotal - discount"/>
</model>
```

Here `v_subtotal` is computed but never written to the database.
Both `discount` and `price_total` reference it, so the
`quantity * price_unit` logic lives in one place instead of being
duplicated across every field that needs it.

Virtual fields are also handy for **correlating** persisted fields.
For instance, generating an email address that matches a contact's
name:

```xml
<model name="res.partner" count="200">
    <field name="v_first" virtual="True" generator="fake.first_name" null_frac="0"/>
    <field name="v_last" virtual="True" generator="fake.last_name" null_frac="0"/>
    <field name="name" eval="v_first + ' ' + v_last"/>
    <field name="email" eval="v_first.lower() + '.' + v_last.lower() + '@example.com'"/>
</model>
```

Here `v_first` and `v_last` are generated once and reused, so every
record's `name` and `email` stay consistent with each other — without
either value being stored on its own.

> **Note:** The `v_` prefix is purely a naming convention. A virtual field
> can have any name (valid python identifier), as long as it doesn't 
> conflict with another field name in the same model block.

## Write Jobs

Use `type="write"` to update records that were created earlier in the
same blueprint, referenced by their `id`/`ref`:

```xml
<!-- Create partners -->
<model name="res.partner" count="500" id="customers">
    <field name="name" generator="fake.company" null_frac="0"/>
</model>
    
<!-- Update those same partners -->
<model name="res.partner" type="write" ref="customers">
    <field name="phone" generator="fake.phone_number"/>
</model>
```

A `write` block without `ref` updates **all** existing records of that
model.

## Blueprint Inheritance

Blueprints support a simplified Odoo-style view inheritance via 
`parent_id`. A child blueprint applies XPath or positional specs 
to its parent's XML definition:

```xml
<record id="custom_blueprint" model="populate.blueprint">
    <field name="name">Custom Blueprint</field>
    <field name="parent_id" ref="base_module.parent_blueprint"/>
    <field name="definition_xml" type="xml">
        <!-- Change record count -->
        <model name="res.partner" position="attributes">
            <attribute name="count">2000</attribute>
        </model>
        <!-- Add a new field to an existing model -->
        <model name="res.partner" position="inside">
            <field name="website" generator="fake.url"/>
        </model>
        <!-- Add a new model after an existing one -->
        <model name="res.partner" position="after">
            <model name="res.users" count="50" id="new_users">
                <field name="name" generator="fake.name"/>
                <field name="login" generator="fake.user_name" unique="True"/>
            </model>
        </model>
    </field>
</record>
```

Supported positions: `attributes`, `inside`, `before`, `after`,
`replace`. XPath expressions (`<xpath expr="..." position="...">`) 
work as well. Chained inheritance (grandchild blueprints)
is supported; circular inheritance is detected and rejected.

## Sessions & Resuming

Each run creates a **Session** that tracks every job and the records it
produced (`populate.model.data`). If execution is interrupted 
(`SIGINT` via `Ctrl+C`/`Cmd+C`, crash), resume where you left off:

```shell
# Resume the most recent unfinished session
odoo-bin populate -d mydb --resume

# Resume a specific session by ID
odoo-bin populate -d mydb --resume 42
```

## Parallel Execution

Pass `-j <N>` (or `-j auto`) to split large jobs across multiple worker
processes. Each job that exceeds the internal batch size is 
automatically divided into sub-jobs distributed to the pool.

Parallelism can be disabled per model block with `parallel="False"` when
the model's constraints require sequential writes.

Platform controlled by the environment variable
`ODOO_POPULATE_MULTIPROCESS_ENABLE` (defaults to `True`).
